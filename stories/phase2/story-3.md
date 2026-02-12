# Story 3: API Key Auth Middleware

**Batch:** 2 | **Est:** 2-3h | **Dependencies:** Story 2

## Description

Implement authentication middleware that validates API keys on every request (except `/health`). Keys are looked up by hash, checked for revocation, and scoped by org/project. The authenticated org_id and project scope are injected into the request context.

## Acceptance Criteria

1. Requests without `Authorization: Bearer lore_sk_...` header return 401 with `{"error": "missing_api_key"}`
2. Requests with an invalid (non-existent hash) key return 401 with `{"error": "invalid_api_key"}`
3. Requests with a revoked key (revoked_at is set) return 401 with `{"error": "key_revoked"}`
4. `GET /health` works without any auth header
5. Authenticated requests have `request.state.org_id` set to the key's org
6. Authenticated requests have `request.state.project` set to the key's project scope (or None if unscoped)
7. Authenticated requests have `request.state.is_root` set correctly
8. `last_used_at` is updated on successful auth (debounced — not every request, but at least once per minute)
9. Project-scoped keys cannot access lessons outside their project (enforced in middleware or endpoint layer)

## Technical Notes

- Implement as FastAPI middleware or dependency (dependency is cleaner for testing)
- SHA-256 hash the incoming key, lookup in `api_keys` table
- Use a simple in-memory cache (TTL ~60s) to avoid DB lookup on every request
- `last_used_at` update can be fire-and-forget (don't block the response)
- Consider a `get_current_key` dependency that returns an `AuthContext` dataclass
