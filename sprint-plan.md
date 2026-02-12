# Sprint Plan — Lore SDK

**Author:** Bob (Scrum Master) | **Date:** 2026-02-12
**Solo dev:** Amit | **Target:** 10 batches, 2-4 hours each
**Flow per batch:** Dev (red-green-refactor) → Code review → Fix → Commit

---

## Overview

| Batch | Focus | Stories | Est. Hours | Depends On |
|-------|-------|---------|------------|------------|
| 1 | Project scaffolding + SQLite store (CRUD) | 1, 2 | 3-4h | — |
| 2 | Embedding engine + semantic query | 3, 4 | 3-4h | Batch 1 |
| 3 | Redaction pipeline | 5 | 2-3h | Batch 1 |
| 4 | Prompt helper + confidence decay + voting | 6, 7 | 3-4h | Batch 2 |
| 5 | Export/import + CLI | 8 | 2-3h | Batch 1 |
| 6 | TypeScript SDK core (store + publish + query) | 9, 10 | 3-4h | Batch 2 |
| 7 | TypeScript embeddings + redaction + prompt helper | 11, 12 | 3-4h | Batch 3, 6 |
| 8 | Both SDKs: README, examples, test polish | 13 | 2-3h | Batch 7 |
| 9 | PyPI + npm publish | 14 | 2-3h | Batch 8 |
| 10 | Launch prep (blog post, HN post) | 15 | 2-3h | Batch 9 |

---

## Batch Details

### Batch 1: Project Scaffolding + SQLite Store
**Goal:** Working Python package with CRUD operations on lessons. No embeddings yet — store and retrieve by ID, list, delete.

- **Story 1:** Python project scaffolding (pyproject.toml, package structure, dev tooling)
- **Story 2:** SQLite store — publish, get, list, delete with in-memory store for tests

### Batch 2: Embedding Engine + Semantic Query
**Goal:** Embed lessons on publish, query by semantic similarity. Hybrid tag + vector search.

- **Story 3:** ONNX MiniLM embedding engine with pluggable interface
- **Story 4:** Semantic query with tag filtering and ranked results

### Batch 3: Redaction Pipeline
**Goal:** Automatic PII/secret stripping on publish.

- **Story 5:** 6-layer regex redaction pipeline with custom pattern support

### Batch 4: Prompt Helper + Confidence Decay + Voting
**Goal:** Complete the query-to-prompt loop. Make lessons decay and support feedback.

- **Story 6:** Prompt helper (`as_prompt`) with token budget
- **Story 7:** Confidence decay function + upvote/downvote

### Batch 5: Export/Import + CLI
**Goal:** Bulk operations and a minimal CLI.

- **Story 8:** JSON export/import + `lore` CLI (publish, query, list, export, import)

### Batch 6: TypeScript SDK Core
**Goal:** Port the store layer and Lore class to TypeScript.

- **Story 9:** TypeScript project scaffolding (tsconfig, package.json, vitest)
- **Story 10:** TypeScript SQLite store + Lore class (publish, get, list, delete)

### Batch 7: TypeScript Embeddings + Redaction + Prompt Helper
**Goal:** Feature parity with Python SDK.

- **Story 11:** TypeScript embedding engine (@xenova/transformers) + semantic query
- **Story 12:** TypeScript redaction pipeline + prompt helper

### Batch 8: README, Examples, Test Polish
**Goal:** Both SDKs are documented and tested to ship quality.

- **Story 13:** README with quickstart, API reference, examples for both SDKs. Test coverage gaps filled.

### Batch 9: PyPI + npm Publish
**Goal:** Both packages live on registries.

- **Story 14:** Publish `lore-sdk` to PyPI and npm. CI setup for future releases.

### Batch 10: Launch Prep
**Goal:** Content ready for launch day.

- **Story 15:** Blog post draft + HN post draft + landing page copy

---

## Key Decisions

1. **No server in MVP.** Library only.
2. **Python first (Batches 1-5), TypeScript second (Batches 6-7).** Python is the primary market.
3. **ONNX, not PyTorch.** 30MB vs 2GB. Non-negotiable.
4. **Brute-force cosine similarity.** Good enough for <100K lessons.
5. **Regex redaction only.** LLM-based redaction is v2.
6. **ULID for IDs.** Sortable, no coordination.

## Risk Register

| Risk | Mitigation |
|------|-----------|
| ONNX model download UX | Progress bar + clear messaging in Story 3 |
| `better-sqlite3` native compilation issues in TS | Test on macOS + Linux + Windows in Story 10 |
| Install size > 50MB target | Track size in CI, alert if exceeded |
