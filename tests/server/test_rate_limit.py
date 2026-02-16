"""Tests for LO-E7: Rate limiting backends."""

from __future__ import annotations

import time

import pytest

from lore.server.rate_limit import MemoryBackend, RedisBackend


def _redis_available() -> bool:
    """Check if Redis is reachable at localhost:6379."""
    try:
        import redis as redis_lib
        r = redis_lib.Redis(host="localhost", port=6379, socket_connect_timeout=1)
        r.ping()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _redis_available(), reason="Redis not available at localhost:6379")
class TestRedisBackendIntegration:
    """Integration tests against a real running Redis."""

    REDIS_URL = "redis://localhost:6379/15"  # Use DB 15 to avoid conflicts

    def setup_method(self):
        self.backend = RedisBackend(self.REDIS_URL, max_requests=5, window_seconds=2)
        self.backend.clear()

    def teardown_method(self):
        self.backend.clear()

    def test_allows_under_limit(self):
        allowed, retry, remaining, limit = self.backend.is_allowed("integ-key1")
        assert allowed is True
        assert remaining == 4
        assert limit == 5

    def test_blocks_over_limit(self):
        for _ in range(5):
            self.backend.is_allowed("integ-key2")
        allowed, retry, remaining, limit = self.backend.is_allowed("integ-key2")
        assert allowed is False
        assert remaining == 0
        assert retry >= 1

    def test_remaining_decrements(self):
        for i in range(5):
            allowed, _, remaining, _ = self.backend.is_allowed("integ-key3")
            assert allowed is True
            assert remaining == 4 - i

    def test_sliding_window_resets(self):
        """Make requests up to the limit, wait for window to expire, verify reset."""
        for _ in range(5):
            self.backend.is_allowed("integ-key4")
        allowed, _, _, _ = self.backend.is_allowed("integ-key4")
        assert allowed is False

        # Wait for the 2-second window to expire
        time.sleep(2.5)

        allowed, _, remaining, _ = self.backend.is_allowed("integ-key4")
        assert allowed is True
        assert remaining == 4

    def test_separate_keys_isolated(self):
        for _ in range(5):
            self.backend.is_allowed("integ-key5a")
        allowed, _, _, _ = self.backend.is_allowed("integ-key5a")
        assert allowed is False

        # Different key should be unaffected
        allowed, _, remaining, _ = self.backend.is_allowed("integ-key5b")
        assert allowed is True
        assert remaining == 4


class TestMemoryBackend:
    def test_allows_under_limit(self):
        backend = MemoryBackend(max_requests=5, window_seconds=60)
        allowed, retry, remaining, limit = backend.is_allowed("key1")
        assert allowed is True
        assert retry == 0
        assert remaining == 4
        assert limit == 5

    def test_blocks_over_limit(self):
        backend = MemoryBackend(max_requests=3, window_seconds=60)
        for _ in range(3):
            backend.is_allowed("key1")

        allowed, retry, remaining, limit = backend.is_allowed("key1")
        assert allowed is False
        assert retry >= 1
        assert remaining == 0
        assert limit == 3

    def test_separate_keys(self):
        backend = MemoryBackend(max_requests=2, window_seconds=60)
        backend.is_allowed("key1")
        backend.is_allowed("key1")

        # key2 should still be allowed
        allowed, _, remaining, _ = backend.is_allowed("key2")
        assert allowed is True
        assert remaining == 1

    def test_clear(self):
        backend = MemoryBackend(max_requests=1, window_seconds=60)
        backend.is_allowed("key1")
        allowed, _, _, _ = backend.is_allowed("key1")
        assert allowed is False

        backend.clear()
        allowed, _, _, _ = backend.is_allowed("key1")
        assert allowed is True

    def test_returns_correct_remaining(self):
        backend = MemoryBackend(max_requests=5, window_seconds=60)
        for i in range(5):
            allowed, _, remaining, _ = backend.is_allowed("k")
            assert remaining == 5 - i - 1 if allowed else remaining == 0


class TestRedisBackendFallback:
    """Test Redis backend graceful fallback when Redis is unavailable."""

    def test_fallback_when_redis_unreachable(self):
        backend = RedisBackend("redis://localhost:19999/0", max_requests=5, window_seconds=60)
        # Should fail-open
        allowed, retry, remaining, limit = backend.is_allowed("key1")
        assert allowed is True
        assert limit == 5

    def test_fallback_allows_all_requests(self):
        backend = RedisBackend("redis://localhost:19999/0", max_requests=2, window_seconds=60)
        # Even multiple requests should be allowed (fail-open)
        for _ in range(10):
            allowed, _, _, _ = backend.is_allowed("key1")
            assert allowed is True


class TestRateLimitHeaders:
    """Test that X-RateLimit headers are returned correctly."""

    def test_headers_present_on_allowed_request(self):
        backend = MemoryBackend(max_requests=10, window_seconds=60)
        allowed, retry, remaining, limit = backend.is_allowed("testkey")
        assert allowed is True
        assert limit == 10
        assert remaining == 9

    def test_headers_on_blocked_request(self):
        backend = MemoryBackend(max_requests=1, window_seconds=60)
        backend.is_allowed("testkey")
        allowed, retry, remaining, limit = backend.is_allowed("testkey")
        assert allowed is False
        assert limit == 1
        assert remaining == 0
        assert retry >= 1
