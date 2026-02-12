# Story 8: Key Management API + CLI

**Batch:** 7 | **Est:** 2-3h | **Dependencies:** Story 3

## Description

Implement API endpoints and CLI commands for managing API keys. Root keys can create sub-keys (optionally project-scoped), list keys, and revoke keys.

## Acceptance Criteria

1. `POST /v1/keys` (root key required) creates a new API key and returns `{"id": "...", "key": "lore_sk_...", "name": "...", "project": "..."}`
2. The raw key is returned ONLY in the creation response — never again
3. `GET /v1/keys` (root key required) returns list of keys with: id, name, key_prefix, project, is_root, created_at, last_used_at, revoked (boolean) — NO key_hash
4. `DELETE /v1/keys/{id}` (root key required) sets `revoked_at` and returns 204
5. Non-root key calling key management endpoints gets 403
6. Cannot revoke the last root key (returns 400 with error message)
7. CLI: `lore keys create --name "agent-1" --project "backend"` creates a key (requires `--api-url` and `--api-key` flags or env vars)
8. CLI: `lore keys list` shows keys in table format
9. CLI: `lore keys revoke <id>` revokes a key
10. Newly created keys work immediately for lesson operations
11. Revoked keys stop working immediately (clear from auth cache)

## Technical Notes

- Server routes in `src/lore/server/routes/keys.py`
- CLI commands extend existing `src/lore/cli.py`
- Use `LORE_API_URL` and `LORE_API_KEY` env vars as defaults for CLI
- Key creation: generate 32 random hex chars, prefix with `lore_sk_`
- On revocation, invalidate the auth cache entry for that key's hash
