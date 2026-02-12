"""API key authentication dependency for FastAPI."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

try:
    from fastapi import HTTPException, Request
except ImportError:
    raise ImportError("FastAPI is required. Install with: pip install lore-sdk[server]")

from lore.server.db import get_pool

logger = logging.getLogger(__name__)

# ── Auth context ───────────────────────────────────────────────────


@dataclass
class AuthContext:
    """Resolved authentication context injected into endpoints."""

    org_id: str
    project: Optional[str]
    is_root: bool
    key_id: str


class AuthError(HTTPException):
    """Auth error that returns {"error": "code"} directly."""

    def __init__(self, error_code: str, status_code: int = 401):
        super().__init__(status_code=status_code, detail=error_code)
        self.error_code = error_code


# ── In-memory cache ────────────────────────────────────────────────

# Cache: key_hash -> (row_dict, monotonic_timestamp)
_key_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
CACHE_TTL_SECONDS = 60.0
CACHE_MAX_SIZE = 10_000

# Debounced last_used_at updates: key_id -> monotonic_timestamp of last fire
_last_used_updates: Dict[str, float] = {}
LAST_USED_DEBOUNCE_SECONDS = 60.0


def _auth_error(error_code: str, status: int = 401) -> AuthError:
    """Create a consistent auth error."""
    return AuthError(error_code=error_code, status_code=status)


async def get_auth_context(request: Request) -> AuthContext:
    """FastAPI dependency that validates the API key and returns AuthContext.

    Usage:
        @app.get("/v1/something")
        async def endpoint(auth: AuthContext = Depends(get_auth_context)):
            ...
    """
    # Extract bearer token
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise _auth_error("missing_api_key")

    raw_key = auth_header[7:]  # Strip "Bearer "

    # Validate prefix
    if not raw_key.startswith("lore_sk_"):
        raise _auth_error("invalid_api_key")

    # Hash the key
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    # Check cache
    cached = _key_cache.get(key_hash)
    if cached is not None:
        row, cached_at = cached
        if time.monotonic() - cached_at < CACHE_TTL_SECONDS:
            return _validate_row(row)

    # DB lookup
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id, org_id, project, is_root, revoked_at, key_hash
               FROM api_keys WHERE key_hash = $1""",
            key_hash,
        )

    if row is None:
        raise _auth_error("invalid_api_key")

    # Convert to dict for caching
    row_dict = dict(row)

    # Timing-safe comparison of hash (defense in depth — DB already matched,
    # but this prevents timing leaks if DB uses non-constant-time comparison)
    if not hmac.compare_digest(row_dict["key_hash"], key_hash):
        raise _auth_error("invalid_api_key")

    # Cache the result (with size limit)
    if len(_key_cache) >= CACHE_MAX_SIZE:
        # Evict oldest entries
        sorted_keys = sorted(_key_cache, key=lambda k: _key_cache[k][1])
        for k in sorted_keys[: len(sorted_keys) // 2]:
            del _key_cache[k]
    _key_cache[key_hash] = (row_dict, time.monotonic())

    ctx = _validate_row(row_dict)

    # Fire-and-forget last_used_at update (debounced)
    _maybe_update_last_used(ctx.key_id)

    return ctx


def _validate_row(row: Dict[str, Any]) -> AuthContext:
    """Check revocation and build AuthContext from a DB row dict."""
    if row.get("revoked_at") is not None:
        raise _auth_error("key_revoked")

    return AuthContext(
        org_id=row["org_id"],
        project=row.get("project"),
        is_root=row.get("is_root", False),
        key_id=row["id"],
    )


def _maybe_update_last_used(key_id: str) -> None:
    """Schedule a debounced last_used_at update."""
    now = time.monotonic()
    last = _last_used_updates.get(key_id, 0.0)
    if now - last < LAST_USED_DEBOUNCE_SECONDS:
        return

    _last_used_updates[key_id] = now

    async def _do_update() -> None:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE api_keys SET last_used_at = now() WHERE id = $1",
                    key_id,
                )
        except Exception:
            logger.debug("Failed to update last_used_at for key %s", key_id, exc_info=True)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_do_update())
    except RuntimeError:
        pass  # No running loop — skip update
