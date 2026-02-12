# Story 11: TypeScript Embedding Engine + Semantic Query

**Batch:** 7 | **Dependencies:** Story 10

## Description
Port the embedding engine and semantic query to TypeScript using `@xenova/transformers`.

## Acceptance Criteria

1. `LocalEmbedder` loads MiniLM-L6-v2 via `@xenova/transformers` and produces 384-dim vectors
2. Model downloads on first use with progress indication
3. `lore.query("text")` returns lessons ranked by cosine similarity
4. `lore.query("text", { tags: ["stripe"] })` filters by tags
5. `lore.query("text", { limit: 3, minConfidence: 0.5 })` respects parameters
6. Confidence decay and vote scoring applied (same formula as Python)
7. Custom embedding function supported: `new Lore({ embeddingFn: myFn })`
8. Query with 1000 lessons returns in < 500ms (Node.js is slower than numpy — relax target)

## Technical Notes
- `@xenova/transformers` runs ONNX in Node.js — same model as Python SDK
- Cosine similarity: manual implementation or use a small math utility
- Decay function: port directly from Python
