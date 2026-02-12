# Story 10: Integration Tests + Rate Limiting + Error Handling

**Batch:** 9 | **Est:** 3-4h | **Dependencies:** Stories 1-9

## Description

Add end-to-end integration tests that exercise the full flow (SDK → server → Postgres → response), implement rate limiting, and harden error handling across all endpoints.

## Acceptance Criteria

1. Integration test: Python SDK publishes a lesson via RemoteStore, queries it back, verifies match
2. Integration test: Two different API keys (different projects) can't see each other's lessons
3. Integration test: Revoked key gets 401 immediately
4. Integration test: Upvote/downvote via SDK updates server-side counts
5. Integration test: Export from one org, import to another — lessons transfer correctly
6. Rate limiting: >100 requests/minute from one key returns 429 with `Retry-After` header
7. Rate limiting: different keys have independent rate limits
8. All 4xx/5xx responses have consistent JSON shape: `{"error": "error_code", "message": "Human-readable description"}`
9. Server returns 400 (not 500) for malformed JSON bodies
10. Server returns 413 for request bodies > 1MB
11. All existing Phase 1 tests still pass (no regressions)
12. Integration tests run via `pytest tests/integration/` against Docker Compose

## Technical Notes

- Integration tests in `tests/integration/test_remote.py`
- Rate limiting: use in-memory sliding window (dict of key_hash → request timestamps)
- Implement rate limiting as FastAPI middleware
- Use `pytest-docker` or manual `docker compose up` in CI
- Error handling: add a global exception handler in FastAPI that catches and formats errors
- Test with `httpx` test client for unit tests, real HTTP for integration tests
