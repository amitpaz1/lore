# Story 3: ONNX MiniLM Embedding Engine

**Batch:** 2 | **Dependencies:** Story 1

## Description
Implement the embedding layer with `all-MiniLM-L6-v2` via `onnxruntime`. Define the abstract `Embedder` interface, implement `LocalEmbedder`. Model downloads on first use with progress indication.

## Acceptance Criteria

1. `Embedder` abstract base class defines `embed(text: str) -> list[float]` and `embed_batch(texts: list[str]) -> list[list[float]]`
2. `LocalEmbedder` loads MiniLM-L6-v2 ONNX model and produces 384-dim vectors
3. First-use model download shows progress (tqdm or similar) and caches to `~/.lore/models/`
4. `embed("hello world")` returns a list of 384 floats
5. Embedding of identical text produces identical vectors
6. `Lore(embedding_fn=custom_fn)` allows user-provided embedding function
7. Model + onnxruntime total < 120MB installed
8. Embedding a single sentence takes < 50ms on CPU (assert in test with tolerance)

## Technical Notes
- Use `onnxruntime` (not `sentence-transformers` — too heavy)
- Model: `all-MiniLM-L6-v2` exported to ONNX — use from HuggingFace hub or bundle
- Tokenizer: use `tokenizers` package (fast, small) or bundle a simple tokenizer
- Consider `onnxruntime` vs `onnxruntime-gpu` — default to CPU-only
