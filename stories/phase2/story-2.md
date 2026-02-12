# Story 2: Database Schema and Migration

**Batch:** 1 | **Est:** 1.5-2h | **Dependencies:** Story 1

## Description

Create the PostgreSQL schema for orgs, api_keys, and lessons tables. Include a migration script that runs on startup or via CLI. The lessons table must support pgvector embeddings (384 dimensions).

## Acceptance Criteria

1. Migration creates `orgs` table with: id (TEXT PK), name (TEXT), created_at (TIMESTAMPTZ)
2. Migration creates `api_keys` table with: id, org_id (FK), name, key_hash, key_prefix, project (nullable), is_root, revoked_at, created_at, last_used_at
3. Migration creates `lessons` table with: id, org_id (FK), problem, resolution, context, tags (JSONB), confidence (REAL), source, project, embedding (vector(384)), created_at, updated_at, expires_at, upvotes, downvotes, meta (JSONB)
4. Index exists on `api_keys(key_hash)`
5. Index exists on `lessons(org_id)` and `lessons(org_id, project)`
6. pgvector cosine similarity index exists on `lessons.embedding`
7. Migration is idempotent — running it twice doesn't error
8. `POST /v1/org/init` creates an org and returns a root API key (key shown once, hash stored)
9. Calling `/v1/org/init` when an org already exists returns 409 Conflict

## Technical Notes

- Migration file at `migrations/001_initial.sql`
- Run migrations via `db.py` on app startup (simple approach — no Alembic for now)
- Use ULIDs for all IDs (use `python-ulid` or `ulid-py`)
- API key format: `lore_sk_{32 random hex chars}`
- Hash keys with SHA-256 before storage
- Store first 12 chars as `key_prefix` for display purposes
