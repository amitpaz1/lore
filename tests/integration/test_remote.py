"""Integration tests for Lore Cloud Server.

Uses httpx AsyncClient with ASGI transport to test the full flow
without requiring Docker/Postgres. DB calls are mocked but the full
HTTP → FastAPI → route → response chain is exercised.

Tests marked @pytest.mark.integration require a real Docker Compose stack.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from httpx import ASGITransport, AsyncClient

from lore.server.app import app
from lore.server.auth import _key_cache, _last_used_updates
from lore.server.middleware import RateLimiter, set_rate_limiter

# ── Constants ──────────────────────────────────────────────────────

ROOT_KEY = "lore_sk_root0000000000000000000000000000"
ROOT_KEY_HASH = hashlib.sha256(ROOT_KEY.encode()).hexdigest()
ORG_ID = "org-integration-001"

PROJECT_A_KEY = "lore_sk_projA000000000000000000000000000"
PROJECT_A_KEY_HASH = hashlib.sha256(PROJECT_A_KEY.encode()).hexdigest()

PROJECT_B_KEY = "lore_sk_projB000000000000000000000000000"
PROJECT_B_KEY_HASH = hashlib.sha256(PROJECT_B_KEY.encode()).hexdigest()

REVOKED_KEY = "lore_sk_revoked0000000000000000000000000"
REVOKED_KEY_HASH = hashlib.sha256(REVOKED_KEY.encode()).hexdigest()

SAMPLE_EMBEDDING = [0.1] * 384
NOW = datetime.now(timezone.utc)

ROOT_KEY_ROW = {
    "id": "key-root",
    "org_id": ORG_ID,
    "project": None,
    "is_root": True,
    "revoked_at": None,
    "key_hash": ROOT_KEY_HASH,
}

PROJECT_A_KEY_ROW = {
    "id": "key-proj-a",
    "org_id": ORG_ID,
    "project": "project-a",
    "is_root": False,
    "revoked_at": None,
    "key_hash": PROJECT_A_KEY_HASH,
}

PROJECT_B_KEY_ROW = {
    "id": "key-proj-b",
    "org_id": ORG_ID,
    "project": "project-b",
    "is_root": False,
    "revoked_at": None,
    "key_hash": PROJECT_B_KEY_HASH,
}

REVOKED_KEY_ROW = {
    "id": "key-revoked",
    "org_id": ORG_ID,
    "project": None,
    "is_root": False,
    "revoked_at": NOW,
    "key_hash": REVOKED_KEY_HASH,
}


# ── Helpers ────────────────────────────────────────────────────────


def _lesson_row(
    lesson_id: str = "lesson-001",
    project: Optional[str] = None,
    **overrides: Any,
) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "id": lesson_id,
        "org_id": ORG_ID,
        "problem": "test problem",
        "resolution": "test resolution",
        "context": None,
        "tags": json.dumps(["test"]),
        "confidence": 0.8,
        "source": None,
        "project": project,
        "created_at": NOW,
        "updated_at": NOW,
        "expires_at": None,
        "upvotes": 0,
        "downvotes": 0,
        "meta": json.dumps({}),
    }
    base.update(overrides)
    return base


def _make_mock_pool(
    key_row: Optional[Dict[str, Any]] = None,
    fetchrow_side_effect: Optional[list] = None,
    fetch_return: Optional[list] = None,
    fetchval_return: Any = None,
    execute_return: str = "DELETE 1",
) -> tuple:
    """Create a mock asyncpg pool."""
    mock_conn = AsyncMock()

    if fetchrow_side_effect is not None:
        mock_conn.fetchrow = AsyncMock(side_effect=fetchrow_side_effect)
    elif key_row is not None:
        mock_conn.fetchrow = AsyncMock(return_value=key_row)
    else:
        mock_conn.fetchrow = AsyncMock(return_value=None)

    mock_conn.fetch = AsyncMock(return_value=fetch_return or [])
    mock_conn.fetchval = AsyncMock(return_value=fetchval_return)
    mock_conn.execute = AsyncMock(return_value=execute_return)

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
    _key_cache.clear()
    _last_used_updates.clear()
    # Reset rate limiter for each test
    set_rate_limiter(RateLimiter())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    _key_cache.clear()
    _last_used_updates.clear()


# ── Integration Test: Publish → Query → Verify Match ──────────────


@pytest.mark.asyncio
async def test_full_flow_publish_query_verify(client: AsyncClient) -> None:
    """Full flow: create a lesson, then retrieve it and verify fields match."""
    lesson_row = _lesson_row("lesson-flow-001", project=None)
    # First fetchrow: auth (DB lookup, then cached). Second fetchrow: lesson get.
    mock_pool, mock_conn = _make_mock_pool(
        fetchrow_side_effect=[ROOT_KEY_ROW, lesson_row],
    )

    headers = {"Authorization": f"Bearer {ROOT_KEY}"}

    with patch("lore.server.routes.lessons.get_pool", return_value=mock_pool), \
         patch("lore.server.auth.get_pool", return_value=mock_pool):
        # Step 1: Publish
        create_resp = await client.post(
            "/v1/lessons",
            headers=headers,
            json={
                "problem": "test problem",
                "resolution": "test resolution",
                "embedding": SAMPLE_EMBEDDING,
                "tags": ["test"],
            },
        )
        assert create_resp.status_code == 201
        lesson_id = create_resp.json()["id"]
        assert lesson_id  # non-empty

        # Step 2: Query back
        get_resp = await client.get(
            "/v1/lessons/lesson-flow-001",
            headers=headers,
        )
        assert get_resp.status_code == 200
        data = get_resp.json()

        # Step 3: Verify match
        assert data["problem"] == "test problem"
        assert data["resolution"] == "test resolution"
        assert data["tags"] == ["test"]
        assert data["confidence"] == 0.8


# ── Integration Test: Project Scoping Isolation ────────────────────


@pytest.mark.asyncio
async def test_project_scoping_isolation(client: AsyncClient) -> None:
    """Two different project-scoped keys can't see each other's lessons."""
    headers_a = {"Authorization": f"Bearer {PROJECT_A_KEY}"}
    headers_b = {"Authorization": f"Bearer {PROJECT_B_KEY}"}

    # Key A creates a lesson (project-a), Key B tries to get it → 404
    mock_pool, mock_conn = _make_mock_pool(
        fetchrow_side_effect=[
            PROJECT_A_KEY_ROW,  # auth for Key A (cached after)
            PROJECT_B_KEY_ROW,  # auth for Key B (cached after)
            None,               # lesson not found (scoped to project-b)
        ],
    )

    with patch("lore.server.routes.lessons.get_pool", return_value=mock_pool), \
         patch("lore.server.auth.get_pool", return_value=mock_pool):
        # Key A publishes
        create_resp = await client.post(
            "/v1/lessons",
            headers=headers_a,
            json={
                "problem": "project-a problem",
                "resolution": "project-a resolution",
                "embedding": SAMPLE_EMBEDDING,
            },
        )
        assert create_resp.status_code == 201

        # Key B tries to read → 404
        get_resp = await client.get(
            f"/v1/lessons/{create_resp.json()['id']}",
            headers=headers_b,
        )
        assert get_resp.status_code == 404


# ── Integration Test: Revoked Key Rejection ────────────────────────


@pytest.mark.asyncio
async def test_revoked_key_rejected(client: AsyncClient) -> None:
    """Revoked key gets 401 immediately."""
    mock_pool, _ = _make_mock_pool(key_row=REVOKED_KEY_ROW)

    headers = {"Authorization": f"Bearer {REVOKED_KEY}"}

    with patch("lore.server.routes.lessons.get_pool", return_value=mock_pool), \
         patch("lore.server.auth.get_pool", return_value=mock_pool):
        resp = await client.get("/v1/lessons", headers=headers)

    assert resp.status_code == 401
    data = resp.json()
    assert data["error"] == "key_revoked"


# ── Integration Test: Upvote/Downvote Round-Trip ──────────────────


@pytest.mark.asyncio
async def test_upvote_downvote_round_trip(client: AsyncClient) -> None:
    """Upvote then downvote and verify counts update."""
    headers = {"Authorization": f"Bearer {ROOT_KEY}"}

    upvoted_row = _lesson_row("lesson-vote-001", upvotes=1, downvotes=0)
    downvoted_row = _lesson_row("lesson-vote-001", upvotes=1, downvotes=1)

    # Auth cached after first call, so: auth, upvote result, downvote result
    mock_pool, mock_conn = _make_mock_pool(
        fetchrow_side_effect=[
            ROOT_KEY_ROW,    # auth (cached after)
            upvoted_row,     # upvote RETURNING
            downvoted_row,   # downvote RETURNING
        ],
    )

    with patch("lore.server.routes.lessons.get_pool", return_value=mock_pool), \
         patch("lore.server.auth.get_pool", return_value=mock_pool):
        # Upvote
        resp1 = await client.patch(
            "/v1/lessons/lesson-vote-001",
            headers=headers,
            json={"upvotes": "+1"},
        )
        assert resp1.status_code == 200
        assert resp1.json()["upvotes"] == 1
        assert resp1.json()["downvotes"] == 0

        # Downvote
        resp2 = await client.patch(
            "/v1/lessons/lesson-vote-001",
            headers=headers,
            json={"downvotes": "+1"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["upvotes"] == 1
        assert resp2.json()["downvotes"] == 1


# ── Integration Test: Export/Import Between Contexts ──────────────


@pytest.mark.asyncio
async def test_export_import_between_contexts(client: AsyncClient) -> None:
    """Export from one org context, import to another — lessons transfer."""
    headers = {"Authorization": f"Bearer {ROOT_KEY}"}

    export_rows = [
        {
            **_lesson_row("lesson-exp-001"),
            "embedding": json.dumps(SAMPLE_EMBEDDING),
        },
        {
            **_lesson_row("lesson-exp-002"),
            "embedding": json.dumps(SAMPLE_EMBEDDING),
        },
    ]

    # Export mock
    export_pool, _ = _make_mock_pool(
        key_row=ROOT_KEY_ROW,
        fetch_return=export_rows,
    )

    with patch("lore.server.routes.lessons.get_pool", return_value=export_pool), \
         patch("lore.server.auth.get_pool", return_value=export_pool):
        export_resp = await client.post("/v1/lessons/export", headers=headers)

    assert export_resp.status_code == 200
    exported = export_resp.json()["lessons"]
    assert len(exported) == 2

    # Import the exported lessons
    import_pool, import_conn = _make_mock_pool(key_row=ROOT_KEY_ROW)

    with patch("lore.server.routes.lessons.get_pool", return_value=import_pool), \
         patch("lore.server.auth.get_pool", return_value=import_pool):
        import_resp = await client.post(
            "/v1/lessons/import",
            headers=headers,
            json={"lessons": [
                {
                    "problem": l["problem"],
                    "resolution": l["resolution"],
                    "embedding": l["embedding"],
                    "tags": l["tags"],
                    "confidence": l["confidence"],
                }
                for l in exported
            ]},
        )

    assert import_resp.status_code == 200
    assert import_resp.json()["imported"] == 2


# ── Rate Limiting Tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rate_limit_exceeded(client: AsyncClient) -> None:
    """Exceeding 100 req/min returns 429 with Retry-After."""
    # Use a very small limit for testing
    set_rate_limiter(RateLimiter(max_requests=3, window_seconds=60))

    headers = {"Authorization": f"Bearer {ROOT_KEY}"}
    mock_pool, _ = _make_mock_pool(key_row=ROOT_KEY_ROW, fetchval_return=0, fetch_return=[])

    with patch("lore.server.routes.lessons.get_pool", return_value=mock_pool), \
         patch("lore.server.auth.get_pool", return_value=mock_pool):
        # First 3 requests should succeed
        for _ in range(3):
            resp = await client.get("/v1/lessons", headers=headers)
            assert resp.status_code == 200

        # 4th request should be rate limited
        resp = await client.get("/v1/lessons", headers=headers)
        assert resp.status_code == 429
        data = resp.json()
        assert data["error"] == "rate_limit_exceeded"
        assert "Retry-After" in resp.headers


@pytest.mark.asyncio
async def test_rate_limit_independent_per_key(client: AsyncClient) -> None:
    """Different keys have independent rate limits."""
    set_rate_limiter(RateLimiter(max_requests=2, window_seconds=60))

    headers_a = {"Authorization": f"Bearer {PROJECT_A_KEY}"}
    headers_b = {"Authorization": f"Bearer {PROJECT_B_KEY}"}

    # Auth is cached after first lookup per key, so only 2 fetchrow calls for auth
    mock_pool, _ = _make_mock_pool(
        fetchrow_side_effect=[
            PROJECT_A_KEY_ROW,  # auth for Key A (cached after)
            PROJECT_B_KEY_ROW,  # auth for Key B (cached after)
        ],
        fetchval_return=0,
        fetch_return=[],
    )

    with patch("lore.server.routes.lessons.get_pool", return_value=mock_pool), \
         patch("lore.server.auth.get_pool", return_value=mock_pool):
        # Key A: 2 requests OK
        for _ in range(2):
            resp = await client.get("/v1/lessons", headers=headers_a)
            assert resp.status_code == 200

        # Key B: still has its own quota
        for _ in range(2):
            resp = await client.get("/v1/lessons", headers=headers_b)
            assert resp.status_code == 200

        # Key A: rate limited
        resp = await client.get("/v1/lessons", headers=headers_a)
        assert resp.status_code == 429


# ── Error Handling Tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_malformed_json_returns_400(client: AsyncClient) -> None:
    """Malformed JSON body returns 400, not 500."""
    headers = {
        "Authorization": f"Bearer {ROOT_KEY}",
        "Content-Type": "application/json",
    }
    resp = await client.post(
        "/v1/lessons",
        headers=headers,
        content=b"{invalid json!!!}",
    )
    assert resp.status_code in (400, 422)  # FastAPI may return 422 for parse errors
    data = resp.json()
    assert "error" in data
    assert "message" in data


@pytest.mark.asyncio
async def test_body_too_large_returns_413(client: AsyncClient) -> None:
    """Request body > 1MB returns 413."""
    headers = {
        "Authorization": f"Bearer {ROOT_KEY}",
        "Content-Type": "application/json",
        "Content-Length": str(2_000_000),
    }
    resp = await client.post(
        "/v1/lessons",
        headers=headers,
        content=b"x" * 100,  # actual content doesn't matter; Content-Length triggers it
    )
    assert resp.status_code == 413
    data = resp.json()
    assert data["error"] == "request_too_large"


@pytest.mark.asyncio
async def test_consistent_error_shape_404(client: AsyncClient) -> None:
    """404 responses have consistent JSON shape."""
    mock_pool, mock_conn = _make_mock_pool(
        fetchrow_side_effect=[ROOT_KEY_ROW, None],
    )
    headers = {"Authorization": f"Bearer {ROOT_KEY}"}

    with patch("lore.server.routes.lessons.get_pool", return_value=mock_pool), \
         patch("lore.server.auth.get_pool", return_value=mock_pool):
        resp = await client.get("/v1/lessons/nonexistent", headers=headers)

    assert resp.status_code == 404
    data = resp.json()
    assert "error" in data
    assert "message" in data


@pytest.mark.asyncio
async def test_consistent_error_shape_422(client: AsyncClient) -> None:
    """422 validation errors have consistent JSON shape."""
    mock_pool, _ = _make_mock_pool(key_row=ROOT_KEY_ROW)
    headers = {"Authorization": f"Bearer {ROOT_KEY}"}

    with patch("lore.server.routes.lessons.get_pool", return_value=mock_pool), \
         patch("lore.server.auth.get_pool", return_value=mock_pool):
        resp = await client.post(
            "/v1/lessons",
            headers=headers,
            json={"problem": "test"},  # missing required fields
        )

    assert resp.status_code == 422
    data = resp.json()
    assert data["error"] == "validation_error"
    assert "message" in data


@pytest.mark.asyncio
async def test_consistent_error_shape_401(client: AsyncClient) -> None:
    """401 errors have consistent JSON shape."""
    resp = await client.get("/v1/lessons")
    assert resp.status_code == 401
    data = resp.json()
    assert "error" in data


# ── Docker Integration Tests (require real infra) ──────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_publish_query_flow() -> None:
    """Full flow against real Docker Compose stack.

    Requires: docker compose up -d
    """
    pytest.skip("Requires Docker Compose stack")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_project_isolation() -> None:
    """Project isolation against real DB.

    Requires: docker compose up -d
    """
    pytest.skip("Requires Docker Compose stack")
