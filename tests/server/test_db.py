"""Tests for database module — unit tests without actual Postgres."""

from __future__ import annotations

import pytest

import lore.server.db as db_module
from lore.server.db import get_pool


@pytest.mark.asyncio
async def test_get_pool_raises_when_not_initialized():
    """get_pool should raise RuntimeError when pool hasn't been created."""
    old_pool = db_module._pool
    db_module._pool = None
    try:
        with pytest.raises(RuntimeError, match="not initialized"):
            await get_pool()
    finally:
        db_module._pool = old_pool
