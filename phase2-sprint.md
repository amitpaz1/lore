# Phase 2 Sprint Plan — Lore Cloud + MCP

**Scrum Master:** Bob | **Date:** 2026-02-12
**Solo dev:** Amit | **Estimated duration:** 10 batches (~30-40 hours)
**Repo:** `/home/amit/projects/agentmemory/`

---

## Sprint Overview

| Batch | Focus | Stories | Est. Hours | Dependencies |
|-------|-------|---------|------------|--------------|
| 1 | FastAPI skeleton + Postgres schema + Docker Compose | 1, 2 | 3-4h | None |
| 2 | Auth middleware (API key hashing, validation, scoping) | 3 | 2-3h | Batch 1 |
| 3 | Lesson CRUD endpoints | 4 | 3-4h | Batch 2 |
| 4 | Search endpoint (pgvector + decay scoring) | 5 | 3-4h | Batch 3 |
| 5 | Python RemoteStore | 6 | 3-4h | Batch 4 |
| 6 | TypeScript RemoteStore | 7 | 2-3h | Batch 4 |
| 7 | Key management endpoints + CLI | 8 | 2-3h | Batch 2 |
| 8 | MCP server | 9 | 3-4h | Batch 5 |
| 9 | Integration tests, rate limiting, error handling | 10 | 3-4h | Batches 1-8 |
| 10 | Docker image + deployment + docs | 11 | 3-4h | Batch 9 |

**Total estimated: ~28-37 hours (~10-12 working sessions)**

---

## Dependency Graph

```
Batch 1 (skeleton + schema + docker)
  └─► Batch 2 (auth middleware)
        ├─► Batch 3 (CRUD endpoints)
        │     └─► Batch 4 (search endpoint)
        │           ├─► Batch 5 (Python RemoteStore)
        │           │     └─► Batch 8 (MCP server)
        │           └─► Batch 6 (TypeScript RemoteStore)
        └─► Batch 7 (key management)
                          All ─► Batch 9 (integration tests)
                                   └─► Batch 10 (deploy + docs)
```

**Parallelizable:** Batches 5 & 6 can run in parallel. Batch 7 can run any time after Batch 2.

---

## BMAD Flow Per Batch

Each batch follows:
1. **Dev** — Red-green-refactor (write failing test → implement → refactor)
2. **Code Review** — QA persona reviews the diff
3. **Fix** — Address review findings
4. **Commit** — Clean commit with conventional message

---

## Batch Details

### Batch 1: FastAPI Skeleton + Postgres Schema + Docker Compose
**Stories:** [story-1](stories/phase2/story-1.md), [story-2](stories/phase2/story-2.md)
**Goal:** `docker compose up` starts FastAPI + Postgres with pgvector, health endpoint returns 200.

- Story 1: Docker Compose with FastAPI + pgvector Postgres
- Story 2: Database schema (orgs, api_keys, lessons tables) with migration

### Batch 2: Auth Middleware
**Stories:** [story-3](stories/phase2/story-3.md)
**Goal:** Every endpoint (except health) requires a valid, non-revoked API key. Key scoping by org and project.

- Story 3: API key auth middleware with hashing, validation, and project scoping

### Batch 3: Lesson CRUD Endpoints
**Stories:** [story-4](stories/phase2/story-4.md)
**Goal:** Full CRUD for lessons via REST API with org/project scoping.

- Story 4: Lesson publish, get, update, delete, list endpoints

### Batch 4: Search Endpoint
**Stories:** [story-5](stories/phase2/story-5.md)
**Goal:** POST /v1/lessons/search returns lessons ranked by cosine similarity × confidence decay.

- Story 5: Vector search with pgvector + decay scoring + tag filtering

### Batch 5: Python RemoteStore
**Stories:** [story-6](stories/phase2/story-6.md)
**Goal:** `Lore(store="remote", api_url=..., api_key=...)` works identically to local store.

- Story 6: Python RemoteStore implementing Store interface over HTTP

### Batch 6: TypeScript RemoteStore
**Stories:** [story-7](stories/phase2/story-7.md)
**Goal:** TypeScript SDK gets RemoteStore with same behavior as Python.

- Story 7: TypeScript RemoteStore implementation

### Batch 7: Key Management Endpoints + CLI
**Stories:** [story-8](stories/phase2/story-8.md)
**Goal:** Root keys can create/list/revoke sub-keys. CLI `lore keys` commands work.

- Story 8: Key management API + CLI commands

### Batch 8: MCP Server
**Stories:** [story-9](stories/phase2/story-9.md)
**Goal:** `lore mcp` starts MCP server with save_lesson, recall_lessons, upvote, downvote tools.

- Story 9: MCP server exposing Lore operations as tools

### Batch 9: Integration Tests + Rate Limiting + Error Handling
**Stories:** [story-10](stories/phase2/story-10.md)
**Goal:** End-to-end tests, 429 rate limiting, proper error responses across all endpoints.

- Story 10: Integration test suite, rate limiting, error handling hardening

### Batch 10: Docker Image + Deployment + Docs
**Stories:** [story-11](stories/phase2/story-11.md)
**Goal:** Published Docker image, fly.io deployment, updated README + API docs + MCP setup guide.

- Story 11: Production Docker image, deployment, and documentation

---

## File Structure (New)

```
src/lore/server/
├── __init__.py
├── app.py            # FastAPI app, lifespan, middleware
├── auth.py           # API key validation
├── config.py         # Env-based config
├── db.py             # asyncpg connection pool, queries
├── models.py         # Pydantic request/response models
└── routes/
    ├── __init__.py
    ├── lessons.py    # CRUD + search
    ├── keys.py       # Key management
    └── org.py        # Org init

src/lore/store/remote.py   # RemoteStore (Python)
src/lore/mcp/
├── __init__.py
└── server.py              # MCP server

ts/src/store/remote.ts     # RemoteStore (TypeScript)

migrations/
├── 001_initial.sql

docker-compose.yml
Dockerfile.server
```

---

## Risk Notes

- **pgvector IVFFlat index** requires training on existing data. For <10K lessons, use exact search (no index) or HNSW instead. Decide in Batch 4.
- **Embedding dimension** must match SDK's model (384 for all-MiniLM-L6-v2). Validate in Batch 4.
- **httpx vs requests** for RemoteStore — use httpx (async support, connection pooling). Already a lightweight dep.
