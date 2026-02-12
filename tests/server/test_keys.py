"""Tests for key management endpoints."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from httpx import ASGITransport, AsyncClient

from lore.server.app import app


RAW_KEY = "lore_sk_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
KEY_HASH = hashlib.sha256(RAW_KEY.encode()).hexdigest()


def _valid_key_row(org_id="org-1", project=None, is_root=True, revoked_at=None):
    return {
        "id": "key-1",
        "org_id": org_id,
        "project": project,
        "is_root": is_root,
        "revoked_at": revoked_at,
        "key_hash": KEY_HASH,
    }


def _make_mock_pool(fetchrow_return=None, fetch_return=None, fetchval_return=None, execute_return=None):
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=fetchrow_return)
    mock_conn.fetch = AsyncMock(return_value=fetch_return or [])
    mock_conn.fetchval = AsyncMock(return_value=fetchval_return)
    mock_conn.execute = AsyncMock(return_value=execute_return or "UPDATE 1")

    # Mock transaction context manager
    mock_tx = AsyncMock()
    mock_tx.__aenter__ = AsyncMock(return_value=mock_tx)
    mock_tx.__aexit__ = AsyncMock(return_value=False)
    mock_conn.transaction = MagicMock(return_value=mock_tx)

    mock_pool = AsyncMock()
    acm = AsyncMock()
    acm.__aenter__ = AsyncMock(return_value=mock_conn)
    acm.__aexit__ = AsyncMock(return_value=False)
    mock_pool.acquire = MagicMock(return_value=acm)

    return mock_pool, mock_conn


@pytest_asyncio.fixture
async def client():
    from lore.server.auth import _key_cache, _last_used_updates
    from lore.server.middleware import RateLimiter, set_rate_limiter
    _key_cache.clear()
    _last_used_updates.clear()
    set_rate_limiter(RateLimiter())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    _key_cache.clear()
    _last_used_updates.clear()


def _auth_headers():
    return {"Authorization": f"Bearer {RAW_KEY}"}


# ── Create key ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_key_root_only(client):
    """Non-root key gets 403."""
    row = _valid_key_row(is_root=False)
    mock_pool, mock_conn = _make_mock_pool(fetchrow_return=row)

    with patch("lore.server.auth.get_pool", return_value=mock_pool), \
         patch("lore.server.routes.keys.get_pool", return_value=mock_pool):
        resp = await client.post(
            "/v1/keys",
            json={"name": "test"},
            headers=_auth_headers(),
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_key_success(client):
    """Root key can create a new key."""
    row = _valid_key_row(is_root=True)
    mock_pool, mock_conn = _make_mock_pool(fetchrow_return=row)

    with patch("lore.server.auth.get_pool", return_value=mock_pool), \
         patch("lore.server.routes.keys.get_pool", return_value=mock_pool):
        resp = await client.post(
            "/v1/keys",
            json={"name": "agent-1", "project": "backend"},
            headers=_auth_headers(),
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "agent-1"
    assert data["project"] == "backend"
    assert data["key"].startswith("lore_sk_")
    assert "id" in data


# ── List keys ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_keys_root_only(client):
    row = _valid_key_row(is_root=False)
    mock_pool, _ = _make_mock_pool(fetchrow_return=row)

    with patch("lore.server.auth.get_pool", return_value=mock_pool), \
         patch("lore.server.routes.keys.get_pool", return_value=mock_pool):
        resp = await client.get("/v1/keys", headers=_auth_headers())
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_keys_success(client):
    auth_row = _valid_key_row(is_root=True)
    now = datetime.now(timezone.utc)
    key_rows = [
        {
            "id": "key-1", "name": "root", "key_prefix": "lore_sk_a1b2",
            "project": None, "is_root": True, "created_at": now,
            "last_used_at": now, "revoked_at": None,
        },
    ]
    mock_pool, mock_conn = _make_mock_pool(fetchrow_return=auth_row, fetch_return=key_rows)

    with patch("lore.server.auth.get_pool", return_value=mock_pool), \
         patch("lore.server.routes.keys.get_pool", return_value=mock_pool):
        resp = await client.get("/v1/keys", headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["keys"]) == 1
    assert data["keys"][0]["revoked"] is False
    # Ensure key_hash is NOT in response
    assert "key_hash" not in data["keys"][0]


# ── Revoke key ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revoke_key_root_only(client):
    row = _valid_key_row(is_root=False)
    mock_pool, _ = _make_mock_pool(fetchrow_return=row)

    with patch("lore.server.auth.get_pool", return_value=mock_pool), \
         patch("lore.server.routes.keys.get_pool", return_value=mock_pool):
        resp = await client.delete("/v1/keys/some-id", headers=_auth_headers())
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_revoke_key_not_found(client):
    auth_row = _valid_key_row(is_root=True)
    mock_pool, mock_conn = _make_mock_pool(fetchrow_return=auth_row)

    # First fetchrow is auth, second is key lookup returning None
    call_count = 0
    original_fetchrow = mock_conn.fetchrow

    async def fetchrow_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return auth_row  # auth lookup
        return None  # key not found

    mock_conn.fetchrow = AsyncMock(side_effect=fetchrow_side_effect)

    with patch("lore.server.auth.get_pool", return_value=mock_pool), \
         patch("lore.server.routes.keys.get_pool", return_value=mock_pool):
        resp = await client.delete("/v1/keys/nonexistent", headers=_auth_headers())
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_revoke_last_root_key_blocked(client):
    """Cannot revoke the last active root key."""
    auth_row = _valid_key_row(is_root=True)
    target_row = {"id": "key-1", "is_root": True, "key_hash": KEY_HASH, "revoked_at": None}

    call_count = 0

    async def fetchrow_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return auth_row
        return target_row

    mock_pool, mock_conn = _make_mock_pool(fetchval_return=1)
    mock_conn.fetchrow = AsyncMock(side_effect=fetchrow_side_effect)

    with patch("lore.server.auth.get_pool", return_value=mock_pool), \
         patch("lore.server.routes.keys.get_pool", return_value=mock_pool):
        resp = await client.delete("/v1/keys/key-1", headers=_auth_headers())
    assert resp.status_code == 400
    assert "last root key" in resp.json().get("message", resp.json().get("detail", ""))


@pytest.mark.asyncio
async def test_revoke_key_success(client):
    """Revoke a non-root key succeeds."""
    auth_row = _valid_key_row(is_root=True)
    target_row = {"id": "key-2", "is_root": False, "key_hash": "somehash", "revoked_at": None}

    call_count = 0

    async def fetchrow_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return auth_row
        return target_row

    mock_pool, mock_conn = _make_mock_pool()
    mock_conn.fetchrow = AsyncMock(side_effect=fetchrow_side_effect)

    with patch("lore.server.auth.get_pool", return_value=mock_pool), \
         patch("lore.server.routes.keys.get_pool", return_value=mock_pool):
        resp = await client.delete("/v1/keys/key-2", headers=_auth_headers())
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_revoke_key_invalidates_cache(client):
    """Revoking a key removes it from the auth cache."""
    from lore.server.auth import _key_cache

    auth_row = _valid_key_row(is_root=True)
    target_hash = "target_key_hash_value"
    target_row = {"id": "key-2", "is_root": False, "key_hash": target_hash, "revoked_at": None}

    # Pre-populate cache
    import time
    _key_cache[target_hash] = ({"some": "data"}, time.monotonic())

    call_count = 0

    async def fetchrow_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return auth_row
        return target_row

    mock_pool, mock_conn = _make_mock_pool()
    mock_conn.fetchrow = AsyncMock(side_effect=fetchrow_side_effect)

    with patch("lore.server.auth.get_pool", return_value=mock_pool), \
         patch("lore.server.routes.keys.get_pool", return_value=mock_pool):
        resp = await client.delete("/v1/keys/key-2", headers=_auth_headers())
    assert resp.status_code == 204
    assert target_hash not in _key_cache


@pytest.mark.asyncio
async def test_revoke_already_revoked_key(client):
    """Revoking an already-revoked key returns 400."""
    auth_row = _valid_key_row(is_root=True)
    target_row = {
        "id": "key-2", "is_root": False, "key_hash": "somehash",
        "revoked_at": datetime.now(timezone.utc),
    }

    call_count = 0

    async def fetchrow_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return auth_row
        return target_row

    mock_pool, mock_conn = _make_mock_pool()
    mock_conn.fetchrow = AsyncMock(side_effect=fetchrow_side_effect)

    with patch("lore.server.auth.get_pool", return_value=mock_pool), \
         patch("lore.server.routes.keys.get_pool", return_value=mock_pool):
        resp = await client.delete("/v1/keys/key-2", headers=_auth_headers())
    assert resp.status_code == 400
    assert "already revoked" in resp.json().get("message", resp.json().get("detail", ""))
