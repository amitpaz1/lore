"""Tests for structured JSON logging."""

from __future__ import annotations

import json
import logging

import pytest


def test_json_formatter():
    """JsonFormatter outputs valid JSON with expected fields."""
    from lore.server.logging_config import JsonFormatter

    fmt = JsonFormatter()
    record = logging.LogRecord(
        name="lore.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    record.request_id = "abc-123"  # type: ignore[attr-defined]
    record.org_id = "org1"  # type: ignore[attr-defined]
    record.latency_ms = 42.5  # type: ignore[attr-defined]

    output = fmt.format(record)
    data = json.loads(output)

    assert data["level"] == "INFO"
    assert data["logger"] == "lore.test"
    assert data["message"] == "hello world"
    assert data["request_id"] == "abc-123"
    assert data["org_id"] == "org1"
    assert data["latency_ms"] == 42.5
    assert "timestamp" in data


def test_json_formatter_no_extras():
    """JsonFormatter works without extra fields."""
    from lore.server.logging_config import JsonFormatter

    fmt = JsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.WARNING, pathname="", lineno=0,
        msg="warn", args=(), exc_info=None,
    )
    data = json.loads(fmt.format(record))
    assert data["level"] == "WARNING"
    assert "request_id" not in data


@pytest.mark.asyncio
async def test_request_adds_request_id():
    """Middleware adds X-Request-Id header to responses."""
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")

    from httpx import ASGITransport, AsyncClient

    from lore.server.app import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert "x-request-id" in resp.headers
        # Should be a valid UUID-like string
        assert len(resp.headers["x-request-id"]) > 10


@pytest.mark.asyncio
async def test_request_passes_through_request_id():
    """Middleware uses provided X-Request-Id."""
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")

    from httpx import ASGITransport, AsyncClient

    from lore.server.app import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health", headers={"X-Request-Id": "custom-123"})
        assert resp.headers["x-request-id"] == "custom-123"
