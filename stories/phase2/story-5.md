# Story 5: Search Endpoint with pgvector + Decay Scoring

**Batch:** 4 | **Est:** 3-4h | **Dependencies:** Story 4

## Description

Implement the search endpoint that accepts a pre-computed embedding vector, performs cosine similarity search via pgvector, applies confidence decay, and returns ranked results. This is the core value of the server.

## Acceptance Criteria

1. `POST /v1/lessons/search` accepts `{"embedding": [...], "limit": 5}` and returns lessons ranked by score
2. Score = cosine_similarity × decayed_confidence (same decay formula as Phase 1 SqliteStore)
3. Optional `tags` filter: only returns lessons matching ALL specified tags (AND logic)
4. Optional `project` filter (overridden by key scope if key is project-scoped)
5. Optional `min_confidence` filter (default 0.0) — applies AFTER decay calculation
6. Response includes `score` field on each lesson (float 0-1)
7. Results are ordered by score descending
8. `limit` defaults to 5, max 50
9. Empty embedding or wrong dimension (not 384) returns 422
10. Search with no matching lessons returns `{"lessons": []}` (200, not 404)
11. Latency < 100ms for 1K lessons (local Docker, measured in test)
12. Decay formula: `confidence * exp(-lambda * days_since_update)` where lambda = 0.01 (configurable)

## Technical Notes

- Use pgvector's `<=>` operator for cosine distance: `1 - (embedding <=> query_embedding)` gives similarity
- Decay is computed in SQL: `confidence * exp(-0.01 * EXTRACT(EPOCH FROM (now() - updated_at)) / 86400)`
- For <10K lessons, exact search is fine (skip IVFFlat index — it requires training data)
- Consider HNSW index instead of IVFFlat if index is needed later
- Tag filtering: `tags @> '["tag1", "tag2"]'::jsonb`
