# Technical Architecture — Lore SDK

**Author:** Winston (Architect) | **Date:** 2026-02-12
**Status:** Draft — reviewed and challenged (see Review Notes at bottom)
**Depends on:** [PRD](./prd.md)

---

## 1. Architecture Principle

**Local-first, server-optional.** The MVP is a library, not a service. Everything runs in-process with SQLite. A remote backend is a future extension point, not a launch requirement.

```
┌─────────────────────────────────────────┐
│              Your Agent Code             │
│                                         │
│   from lore import Lore                 │
│   lore = Lore()                         │
│   lore.publish(...)                     │
│   lore.query(...)                       │
│                                         │
├─────────────────────────────────────────┤
│              Lore SDK                    │
│  ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │ Publish   │ │  Query   │ │ Prompt │  │
│  │ Pipeline  │ │  Engine  │ │ Helper │  │
│  └────┬─────┘ └────┬─────┘ └────────┘  │
│       │             │                    │
│  ┌────▼─────────────▼──────────────────┐│
│  │         Redaction Pipeline          ││
│  └────┬────────────────────────────────┘│
│       │                                  │
│  ┌────▼────────────────────────────────┐│
│  │       Storage Backend (pluggable)   ││
│  │  ┌─────────┐  ┌──────────────────┐  ││
│  │  │ SQLite  │  │ (Future: Postgres,│  ││
│  │  │ + FTS5  │  │  Remote API)     │  ││
│  │  └─────────┘  └──────────────────┘  ││
│  └─────────────────────────────────────┘│
│                                          │
│  ┌─────────────────────────────────────┐│
│  │    Embedding Engine (pluggable)     ││
│  │  ┌────────────┐ ┌────────────────┐  ││
│  │  │ Local:     │ │ (Future:       │  ││
│  │  │ MiniLM-L6  │ │  OpenAI, etc.) │  ││
│  │  └────────────┘ └────────────────┘  ││
│  └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

---

## 2. Data Model

### Lesson Schema

```sql
CREATE TABLE lessons (
    id          TEXT PRIMARY KEY,  -- ULID (sortable, no coordination needed)
    problem     TEXT NOT NULL,
    resolution  TEXT NOT NULL,
    context     TEXT,              -- optional freeform context
    tags        TEXT,              -- JSON array: ["stripe", "rate-limit"]
    confidence  REAL DEFAULT 0.5, -- 0.0 to 1.0
    source      TEXT,              -- agent name/id that created this
    project     TEXT,              -- namespace scoping
    embedding   BLOB,              -- float32 vector, serialized
    created_at  TEXT NOT NULL,     -- ISO 8601
    updated_at  TEXT NOT NULL,
    expires_at  TEXT,              -- optional TTL
    upvotes     INTEGER DEFAULT 0,
    downvotes   INTEGER DEFAULT 0,
    meta        TEXT               -- JSON blob for extensibility
);

CREATE INDEX idx_lessons_project ON lessons(project);
CREATE INDEX idx_lessons_tags ON lessons(tags);  -- for LIKE-based tag search
CREATE INDEX idx_lessons_created ON lessons(created_at);
```

### Why SQLite, not a vector DB

For MVP with < 100K lessons:
- SQLite FTS5 handles keyword search
- Brute-force cosine similarity over 100K 384-dim vectors takes ~50ms in Python (numpy) and ~10ms in Rust/WASM
- No server process, no Docker, no config
- Embedding stored as BLOB, similarity computed in application code

**When to graduate:** If users consistently have > 500K lessons OR need sub-10ms queries at scale, add an optional vector DB backend (Qdrant-lite or similar). Not for MVP.

---

## 3. Query/Retrieval Approach

### Hybrid: Semantic + Tag Filtering

```
query("stripe rate limiting", tags=["api"], limit=5)
  │
  ├─ 1. Tag filter (SQL WHERE) → candidate set
  ├─ 2. Embed query string → query vector
  ├─ 3. Cosine similarity against candidates → ranked
  ├─ 4. Apply confidence decay: score *= decay(age, confidence)
  └─ 5. Return top-k with scores
```

**Decay function:**
```python
def decay(lesson, half_life_days=30):
    age_days = (now - lesson.created_at).days
    time_factor = 0.5 ** (age_days / half_life_days)
    vote_factor = 1 + (lesson.upvotes - lesson.downvotes) * 0.1
    return lesson.confidence * time_factor * vote_factor
```

### Why not pure vector search?
Tags provide hard filtering (I only want lessons about "stripe"). Vector search alone would return semantically similar but irrelevant results. The hybrid approach gives precision + recall.

---

## 4. Redaction Pipeline (MVP)

MVP uses regex-based pattern matching. No LLM calls.

```
Input lesson text
  │
  ├─ Layer 1: API key patterns (sk-*, AKIA*, ghp_*, etc.)
  ├─ Layer 2: Email addresses
  ├─ Layer 3: Phone numbers (international formats)
  ├─ Layer 4: IP addresses (v4 and v6)
  ├─ Layer 5: Credit card numbers (Luhn check)
  ├─ Layer 6: Custom patterns (user-defined regex list)
  │
  └─ Output: cleaned text with [REDACTED:api_key], [REDACTED:email], etc.
```

**Implementation:** Single-pass regex replacement. ~1ms per lesson. Patterns loaded once at init.

**Known limitation:** Regex won't catch everything (e.g., "my password is hunter2"). LLM-based redaction is a v2 feature for the cloud tier.

**Custom patterns:**
```python
lore = Lore(
    redact_patterns=[
        (r'ACCT-\d{8}', 'account_id'),  # custom pattern → [REDACTED:account_id]
    ]
)
```

---

## 5. SDK Design

### Python

```python
from lore import Lore

# Zero-config initialization
lore = Lore()  # ~/.lore/default.db

# Or with options
lore = Lore(
    project="my-agent",
    db_path="./my-lessons.db",
    embedding_model="local",  # default; or "openai" with api_key
    redact=True,              # default
)

# Publish
lesson_id = lore.publish(
    problem="Stripe API returns 429 after 100 req/min",
    resolution="Exponential backoff: 1s, 2s, 4s, ... cap at 32s",
    tags=["stripe", "rate-limit"],
    confidence=0.9,
)

# Query
lessons = lore.query(
    "how to handle stripe rate limits",
    tags=["stripe"],        # optional filter
    limit=5,                # default 5
    min_confidence=0.3,     # default 0.0
)

# Use in prompt
prompt_section = lore.as_prompt(lessons, max_tokens=500)

# Feedback
lore.upvote(lesson_id)
lore.downvote(lesson_id)

# Lifecycle
lore.delete(lesson_id)
lessons = lore.list(project="my-agent", limit=50)
```

### TypeScript

```typescript
import { Lore } from 'lore-sdk';

const lore = new Lore(); // same defaults

const id = await lore.publish({
  problem: "OpenAI API times out on >4K token completions",
  resolution: "Set timeout to 120s and enable streaming",
  tags: ["openai", "timeout"],
  confidence: 0.85,
});

const lessons = await lore.query("openai timeout issues", {
  tags: ["openai"],
  limit: 3,
});

const promptSection = lore.asPrompt(lessons, { maxTokens: 500 });
```

### SDK Internals

```
lore-sdk/
├── src/
│   ├── __init__.py          # Lore class (main entry point)
│   ├── store/
│   │   ├── base.py          # Abstract store interface
│   │   ├── sqlite.py        # SQLite implementation
│   │   └── memory.py        # In-memory (for testing)
│   ├── embed/
│   │   ├── base.py          # Abstract embedder interface
│   │   ├── local.py         # MiniLM-L6 via sentence-transformers or onnxruntime
│   │   └── openai.py        # OpenAI embeddings (optional)
│   ├── redact/
│   │   ├── pipeline.py      # Redaction orchestrator
│   │   └── patterns.py      # Built-in regex patterns
│   ├── prompt.py            # as_prompt() formatting
│   └── types.py             # Lesson, QueryResult dataclasses
├── tests/
├── pyproject.toml
└── README.md
```

---

## 6. API Design (for future remote backend)

Not built for MVP, but designed now so the SDK can swap backends seamlessly.

```
POST   /v1/lessons          # Publish
GET    /v1/lessons/search    # Query (body: {query, tags, limit})
GET    /v1/lessons/:id       # Get one
PATCH  /v1/lessons/:id       # Update (upvote, downvote, edit)
DELETE /v1/lessons/:id       # Delete
GET    /v1/lessons           # List (with pagination)
POST   /v1/lessons/export    # Bulk export (JSON)
POST   /v1/lessons/import    # Bulk import (JSON)
```

The SDK's `Store` interface maps 1:1 to these endpoints, so switching from `SqliteStore` to `RemoteStore(url="https://api.lore.dev")` is a one-line change.

---

## 7. Embedding Model Strategy

### MVP: Local model, no API keys needed

**Recommended: `all-MiniLM-L6-v2`**
- 384 dimensions, ~80MB model file
- Good quality for short text (lessons are typically 1-3 sentences)
- Runs via `onnxruntime` (no PyTorch dependency → keeps install small)
- ~5ms per embedding on CPU

**Install size budget:**
- `lore-sdk` package: ~5MB
- `onnxruntime`: ~30MB
- Model file: ~80MB (downloaded on first use, cached)
- Total: ~115MB first run, ~35MB after model cached

**Alternative: Bring your own embeddings**
```python
lore = Lore(embedding_fn=my_custom_embed_function)
```

For TypeScript: use `@xenova/transformers` (ONNX runtime for Node.js) or allow custom embedding function.

---

## 8. Deployment Model

### MVP: Library only (no deployment needed)

```
pip install lore-sdk    # Python
npm install lore-sdk    # TypeScript
```

That's it. No server. No Docker. No cloud account. Data lives in `~/.lore/` or a path you specify.

### Future: Optional self-hosted server

A simple FastAPI/Express server wrapping the SDK for teams that want:
- Shared lessons across machines
- Central lesson store
- Basic auth

```bash
# Future — not MVP
lore serve --port 8765
# Or:
docker run -p 8765:8765 loredev/server
```

### Future: Cloud hosted

- Managed at `api.lore.dev`
- Auth via API keys
- Multi-tenant, per-org isolation
- This is the monetization layer

---

## 9. Framework Integration (Post-MVP)

Thin wrappers, not deep integrations:

```python
# LangChain
from lore.integrations.langchain import LoreMemory
agent = create_react_agent(llm, tools, memory=LoreMemory())

# CrewAI
from lore.integrations.crewai import LoreTool
agent = Agent(tools=[LoreTool()])

# OpenAI Assistants — just use as_prompt() in system message
```

These are < 50 lines each. The SDK does the heavy lifting.

---

## 10. Build Plan (Solo Dev Reality Check)

| Week | Deliverable | Effort |
|------|-------------|--------|
| 1 | Core data model, SQLite store, publish/query (Python) | 3-4 days |
| 2 | Embedding integration (ONNX), redaction pipeline | 3-4 days |
| 3 | Prompt helper, confidence decay, upvote/downvote | 2-3 days |
| 4 | TypeScript port, tests, README, PyPI/npm publish | 4-5 days |
| 5 | Blog post, HN launch, collect feedback | 2-3 days |

**Total: ~5 weeks to a published, usable SDK.**

This is aggressive but feasible for a solo dev because:
- No server to build or deploy
- No auth, no networking, no cloud infra
- SQLite + ONNX are well-understood, no novel engineering
- TypeScript version can share the same architecture/patterns

---

## Review Notes — Challenges to Winston's Output

### What I pushed back on:

1. **Original design included a gRPC server in MVP.** Removed entirely. A library is shippable in weeks. A server adds auth, deployment, monitoring, uptime concerns. The PRD explicitly scoped out hosted/server for v1. The SDK is the product.

2. **Original used ChromaDB as embedded vector store.** Replaced with raw SQLite + numpy cosine similarity. ChromaDB adds a dependency (~200MB) and its own abstractions. For < 100K lessons, brute-force cosine is fast enough and eliminates a dependency. Keep it boring.

3. **Embedding model: original proposed shipping PyTorch + sentence-transformers.** Switched to ONNX runtime. PyTorch alone is ~2GB. ONNX runtime is ~30MB. For a developer tool, install size is a dealbreaker. The quality tradeoff is minimal for short texts.

4. **TypeScript SDK: original proposed a separate Rust core with NAPI bindings.** Killed it. That's a maintenance nightmare for a solo dev. Use `@xenova/transformers` for embeddings and `better-sqlite3` for storage. Native JS, no compile step, works everywhere.

5. **API design was RESTful but over-specified.** Simplified to the minimum endpoints. The API isn't built for MVP anyway — it's a design doc so the SDK's internal interfaces align with a future server.

6. **"Can Amit actually build this in 5 weeks?"** Honestly, yes, IF he stays disciplined about scope. The risk is feature creep (adding the server, adding framework integrations, adding a CLI dashboard). The architecture is intentionally boring — SQLite, regex, cosine similarity, dataclasses. No novel components.

7. **Missing: how to handle the embedding model download.** Added note about first-use download + caching. This needs a good UX — a progress bar and clear messaging, not a silent 80MB download that looks like a hang.
