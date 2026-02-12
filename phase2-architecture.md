# Phase 2 Technical Architecture — Lore Cloud

**Author:** Winston (Architect) | **Date:** 2026-02-12
**Status:** Draft — reviewed and challenged
**Depends on:** [Phase 2 PRD](./phase2-prd.md), [Phase 1 Architecture](./architecture.md)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────┐
│           Agent Code (any machine)                │
│                                                    │
│   lore = Lore(store="remote", api_key="...")       │
│                                                    │
│   ┌──────────────────────────────────────────┐    │
│   │           Lore SDK (unchanged API)        │    │
│   │                                            │    │
│   │  ┌────────────┐  ┌─────────────────────┐  │    │
│   │  │ Redaction   │  │ Embedding (local)   │  │    │
│   │  │ (client)    │  │ (client)            │  │    │
│   │  └──────┬─────┘  └────────┬────────────┘  │    │
│   │         │                  │                │    │
│   │  ┌──────▼──────────────────▼────────────┐  │    │
│   │  │     RemoteStore (new in Phase 2)      │  │    │
│   │  │     HTTP client → Lore Server API     │  │    │
│   │  └──────────────────┬───────────────────┘  │    │
│   └─────────────────────┼──────────────────────┘    │
└─────────────────────────┼──────────────────────────┘
                          │ HTTPS
┌─────────────────────────▼──────────────────────────┐
│              Lore Server (FastAPI)                   │
│                                                      │
│  ┌────────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ Auth        │  │ CRUD     │  │ Query Engine   │  │
│  │ Middleware   │  │ Endpoints│  │ (cosine sim)   │  │
│  └──────┬─────┘  └────┬─────┘  └───────┬────────┘  │
│         │              │                 │            │
│  ┌──────▼──────────────▼─────────────────▼────────┐  │
│  │              PostgreSQL                         │  │
│  │   orgs | api_keys | lessons (with pgvector)    │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

**Key decisions:**
- Redaction + embedding happen client-side (security + simplicity)
- Server is stateless (no embedding model, no redaction logic)
- Server receives pre-computed vectors and redacted text
- PostgreSQL with pgvector for similarity search at scale

---

## 2. Server Stack

**FastAPI (Python).** One server, not two.

Why FastAPI:
- Amit knows Python (Lore SDK is Python-first)
- Async out of the box
- Auto-generates OpenAPI docs
- Same language as SDK = shared types/validation

Why NOT Express:
- Would require maintaining two codebases in two languages
- No shared code with Python SDK
- TypeScript SDK connects via HTTP — doesn't need a JS server

**Dependencies (minimal):**
```
fastapi
uvicorn
asyncpg (or sqlalchemy[asyncio])
pgvector  # PostgreSQL extension
pydantic
python-multipart  # for API key header parsing
```

---

## 3. Database Schema

**PostgreSQL with pgvector extension.**

```sql
-- pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Orgs
CREATE TABLE orgs (
    id          TEXT PRIMARY KEY,          -- ulid
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- API Keys
CREATE TABLE api_keys (
    id          TEXT PRIMARY KEY,          -- ulid
    org_id      TEXT NOT NULL REFERENCES orgs(id),
    name        TEXT NOT NULL,
    key_hash    TEXT NOT NULL,             -- sha256 of the key
    key_prefix  TEXT NOT NULL,             -- first 8 chars for display: "lore_sk_abc..."
    project     TEXT,                      -- NULL = all projects
    is_root     BOOLEAN DEFAULT FALSE,
    revoked_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT now(),
    last_used_at TIMESTAMPTZ
);
CREATE INDEX idx_keys_hash ON api_keys(key_hash);

-- Lessons (mirrors SDK schema + org scoping)
CREATE TABLE lessons (
    id          TEXT PRIMARY KEY,          -- ulid
    org_id      TEXT NOT NULL REFERENCES orgs(id),
    problem     TEXT NOT NULL,
    resolution  TEXT NOT NULL,
    context     TEXT,
    tags        JSONB DEFAULT '[]',
    confidence  REAL DEFAULT 0.5,
    source      TEXT,
    project     TEXT,
    embedding   vector(384),              -- pgvector type
    created_at  TIMESTAMPTZ NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL,
    expires_at  TIMESTAMPTZ,
    upvotes     INTEGER DEFAULT 0,
    downvotes   INTEGER DEFAULT 0,
    meta        JSONB DEFAULT '{}'
);
CREATE INDEX idx_lessons_org ON lessons(org_id);
CREATE INDEX idx_lessons_org_project ON lessons(org_id, project);
CREATE INDEX idx_lessons_embedding ON lessons USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Why Postgres, not SQLite-per-org:**
- pgvector handles similarity search natively (no application-level cosine)
- JSONB for tags enables proper indexing
- Single database, simpler ops
- Fly.io/Railway/Supabase all offer managed Postgres with pgvector

**Why NOT SQLite-per-org:**
- Managing hundreds of SQLite files is operational nightmare
- No native vector search
- Connection pooling doesn't work

---

## 4. API Endpoints

```
# Auth: API key in header
Authorization: Bearer lore_sk_...

# Org management (root key only)
POST   /v1/org/init              # Create org + root key (first-time setup)

# Key management (root key only)  
POST   /v1/keys                  # Create API key
GET    /v1/keys                  # List keys (redacted)
DELETE /v1/keys/:id              # Revoke key

# Lessons (any valid key, scoped by org + optional project)
POST   /v1/lessons               # Publish lesson
GET    /v1/lessons/:id           # Get one
PATCH  /v1/lessons/:id           # Update (upvote, downvote, edit)
DELETE /v1/lessons/:id           # Delete
GET    /v1/lessons               # List (paginated)
POST   /v1/lessons/search        # Query (body: {embedding, tags, limit, min_confidence})
POST   /v1/lessons/export        # Bulk export
POST   /v1/lessons/import        # Bulk import
```

**Search endpoint detail:**
```json
POST /v1/lessons/search
{
    "embedding": [0.1, 0.2, ...],     // 384-dim vector (computed client-side)
    "tags": ["stripe"],                // optional filter
    "project": "backend",             // optional (or from key scope)
    "limit": 5,
    "min_confidence": 0.3
}

Response:
{
    "lessons": [
        {
            "id": "...",
            "problem": "...",
            "resolution": "...",
            "score": 0.87,            // cosine similarity × decay
            ...
        }
    ]
}
```

---

## 5. Auth Model

**Simple API key authentication. No JWT, no OAuth, no sessions.**

```
Key format: lore_sk_{32 random chars}
Example:   lore_sk_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

Storage:   SHA-256 hash only. Raw key shown once at creation, never again.
Lookup:    Hash incoming key → lookup in api_keys table → check not revoked
```

**Scoping:**
- Root key: can manage keys + access all projects
- Project-scoped key: can only read/write lessons in that project
- All keys are org-scoped (key belongs to exactly one org)

**Why not JWT:**
- API keys are simpler for machine-to-machine (agents, not humans)
- No token refresh, no expiry management
- Agents embed the key in config and forget about it
- JWT adds complexity with zero benefit for this use case

**Rate limiting:**
- 100 requests/min per key (configurable)
- Implemented via in-memory sliding window (or Redis if needed later)
- Returns 429 with Retry-After header

---

## 6. RemoteStore SDK Implementation

The existing `Store` interface makes this clean. RemoteStore implements the same abstract methods.

### Python

```python
# lore/store/remote.py
class RemoteStore(BaseStore):
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.session = httpx.Client(
            base_url=self.api_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    def save(self, lesson: Lesson) -> str:
        resp = self.session.post("/v1/lessons", json=lesson.to_dict())
        resp.raise_for_status()
        return resp.json()["id"]

    def search(self, embedding, tags=None, project=None, limit=5, min_confidence=0.0):
        resp = self.session.post("/v1/lessons/search", json={
            "embedding": embedding.tolist(),
            "tags": tags,
            "project": project,
            "limit": limit,
            "min_confidence": min_confidence,
        })
        resp.raise_for_status()
        return [Lesson.from_dict(l) for l in resp.json()["lessons"]]

    def get(self, lesson_id: str) -> Lesson: ...
    def update(self, lesson_id: str, **kwargs): ...
    def delete(self, lesson_id: str): ...
    def list(self, project=None, limit=50, offset=0): ...
```

### TypeScript

```typescript
// src/store/remote.ts
export class RemoteStore implements Store {
    constructor(private apiUrl: string, private apiKey: string) {}

    async save(lesson: Lesson): Promise<string> {
        const resp = await fetch(`${this.apiUrl}/v1/lessons`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${this.apiKey}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify(lesson),
        });
        return (await resp.json()).id;
    }

    async search(params: SearchParams): Promise<Lesson[]> { ... }
    // ... same pattern
}
```

**Key design:** The Lore class doesn't change at all. It already delegates to a Store. We're just adding a new Store implementation.

---

## 7. Hybrid Sync: Deferred (Design Notes Only)

**Not in Phase 2 MVP.** But here's the design direction for Phase 3:

```
HybridStore:
  - local: SqliteStore (cache)
  - remote: RemoteStore (source of truth)
  
  publish() → write to remote, cache locally
  query()   → try remote, fall back to local cache
  sync()    → pull new lessons from remote into local
```

**Hard problems deferred:**
- Conflict resolution (two agents edit same lesson offline)
- Sync ordering (last-write-wins? vector clocks?)
- Offline queue (publish while disconnected, sync later)
- Cache invalidation (when does local become stale?)

Each of these is 3-5 days of work. Combined, it's a full phase.

---

## 8. Deployment

### Self-hosted (Docker)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
EXPOSE 8765
CMD ["uvicorn", "lore.server:app", "--host", "0.0.0.0", "--port", "8765"]
```

```yaml
# docker-compose.yml
services:
  lore:
    image: loredev/server:latest
    ports: ["8765:8765"]
    environment:
      DATABASE_URL: postgresql://lore:lore@db:5432/lore
    depends_on: [db]
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: lore
      POSTGRES_USER: lore
      POSTGRES_PASSWORD: lore
    volumes: ["pgdata:/var/lib/postgresql/data"]
volumes:
  pgdata:
```

**One command:** `docker compose up` — done.

### Managed (fly.io)

- Server: fly.io app (~$5/mo for small VM)
- Database: fly.io Postgres or Supabase (~$0-15/mo)
- **Total infra cost: ~$5-20/mo** to start

Why fly.io:
- `fly deploy` from Dockerfile
- Built-in Postgres with pgvector
- Free tier for low traffic
- Scales simply if needed

Alternative: Railway (similar simplicity, slightly higher cost).

---

## 9. Server File Structure

```
lore-server/              # Could be in same repo as SDK or separate
├── lore/
│   └── server/
│       ├── __init__.py
│       ├── app.py        # FastAPI app, middleware, lifespan
│       ├── auth.py       # API key validation, scoping
│       ├── routes/
│       │   ├── lessons.py    # CRUD + search
│       │   ├── keys.py       # Key management
│       │   └── org.py        # Org init
│       ├── db.py         # Database connection, queries
│       ├── models.py     # Pydantic models for request/response
│       └── config.py     # Environment-based config
├── migrations/           # Alembic or raw SQL
├── Dockerfile
├── docker-compose.yml
└── tests/
```

**Monorepo recommendation:** Keep server in the same repo as SDK (`/server` directory). Shared types, easier to keep in sync, single CI pipeline.

---

## 10. MCP Server (Model Context Protocol)

The MCP server is a **thin wrapper** around the existing Lore SDK. It exposes Lore operations as MCP tools so any MCP-compatible agent gets cross-agent memory without code changes.

### Architecture

```
┌─────────────────────────────────┐
│  MCP Client (Claude Desktop,    │
│  OpenClaw, OpenAI agents, etc.) │
└──────────┬──────────────────────┘
           │ stdio (JSON-RPC)
┌──────────▼──────────────────────┐
│  Lore MCP Server                │
│  (thin wrapper — ~200 lines)    │
│                                  │
│  Tools:                          │
│    save_lesson → lore.publish()  │
│    recall_lessons → lore.query() │
│    upvote_lesson → lore.upvote() │
│    downvote_lesson → lore.downvote() │
│                                  │
│  ┌────────────────────────────┐  │
│  │  Lore SDK (existing)       │  │
│  │  Store: SqliteStore OR     │  │
│  │         RemoteStore        │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
```

### File Structure

```
lore/
└── mcp/
    ├── __init__.py
    └── server.py      # MCP server implementation (~200 lines)
```

`server.py` creates a `Lore` instance based on env vars and registers 4 tools. That's it.

### Store Selection

```python
# Determined by environment variables:
# LORE_STORE=local (default) → SqliteStore
# LORE_STORE=remote → RemoteStore(api_url=LORE_API_URL, api_key=LORE_API_KEY)
# LORE_PROJECT → default project for all operations
```

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "lore": {
      "command": "uvx",
      "args": ["lore-memory", "mcp"],
      "env": {
        "LORE_STORE": "remote",
        "LORE_API_URL": "https://api.lore.dev",
        "LORE_API_KEY": "lore_sk_...",
        "LORE_PROJECT": "my-project"
      }
    }
  }
}
```

For local-only (no server needed):
```json
{
  "mcpServers": {
    "lore": {
      "command": "uvx",
      "args": ["lore-memory", "mcp"]
    }
  }
}
```

### OpenClaw Skill Integration

Lore can be packaged as an OpenClaw skill. The skill's `SKILL.md` tells agents they have memory tools. The MCP server runs as a subprocess.

### Dependencies

One additional dependency: `mcp` (the Python MCP SDK). Already handles stdio transport, tool registration, and JSON-RPC protocol.

---

## 11. Build Plan (3-Week Sprint)

| Day | Task | Notes |
|---|---|---|
| **Week 1: Server** | | |
| D1-2 | FastAPI skeleton, Postgres schema, Docker Compose | Get "hello world" endpoint running with DB |
| D3 | Auth middleware (API key hashing, validation, scoping) | Test with curl |
| D4 | Lesson CRUD endpoints (publish, get, update, delete, list) | Without search |
| D5 | Search endpoint with pgvector cosine similarity + decay | Core value |
| **Week 2: SDK + Integration** | | |
| D6-7 | Python RemoteStore implementation | Test against local server |
| D8 | TypeScript RemoteStore implementation | Same pattern, HTTP client |
| D9 | MCP server implementation + Claude Desktop testing | Thin wrapper, ~1-2 days |
| D10 | Key management endpoints + CLI commands | `lore keys create/list/revoke` |
| D11 | Export/import via API | Bulk endpoints |
| **Week 3: Ship** | | |
| D12-13 | Integration tests, error handling, rate limiting | Edge cases |
| D14 | Docker image build + publish, fly.io deployment | Managed instance live |
| D15 | Docs: README update, self-hosted guide, API reference, MCP setup guide | |
| D16 | Buffer / bug fixes | Something will break |

**Honest assessment:** This is tight but doable because:
- The Store interface already exists — RemoteStore is mostly HTTP calls
- FastAPI + Postgres + pgvector is well-trodden ground
- No novel engineering — just assembling known components
- No frontend, no OAuth, no complex auth flows

**What could blow the timeline:**
- pgvector setup issues (usually straightforward but can surprise)
- Embedding format mismatches between SDK and server
- Auth edge cases (key rotation, concurrent revocation)

---

## Review Notes — Challenges to Winston's Phase 2 Output

### What I pushed back on:

1. **Original proposed separate servers for Python and TypeScript.** Killed it. One FastAPI server. Both SDKs are HTTP clients. Don't build two servers for one API.

2. **Original used JWT + OAuth.** Replaced with simple API keys. Agents don't need OAuth flows. They need a key they can embed in config. JWT adds token refresh complexity for zero benefit in machine-to-machine auth.

3. **Original had Redis, message queues, and worker processes.** All removed. The server is a single FastAPI process talking to Postgres. That handles hundreds of concurrent agents easily. Add complexity only when it breaks.

4. **"Is this overengineered?"** With the cuts above: no. FastAPI + Postgres + pgvector is the minimum viable server stack. You can't go simpler without giving something up.

5. **"Can Amit actually run this?"** Yes. Docker Compose for self-hosted, fly.io for managed. Total ops burden: ~1 hour/month. Postgres is the only stateful component. Back it up.

6. **Infra cost:** $5-20/mo to run the managed instance. Postgres is the main cost. At <1000 users, this is negligible. The cost scales linearly with lessons stored, not with requests (pgvector queries are cheap).

7. **SQLite-per-org was proposed as "simpler."** It's not. Managing N SQLite files, no connection pooling, no native vector search, backup complexity — Postgres is simpler for multi-tenant at every scale above 1.
