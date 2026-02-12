# Story 4: Semantic Query with Tag Filtering

**Batch:** 2 | **Dependencies:** Story 2, Story 3

## Description
Wire embeddings into publish (embed on save) and implement `lore.query()` with hybrid semantic + tag search. Cosine similarity computed in Python with numpy.

## Acceptance Criteria

1. `lore.publish(...)` now computes and stores embedding automatically
2. `lore.query("some text")` returns lessons ranked by cosine similarity
3. `lore.query("text", tags=["stripe"])` filters by tags before ranking
4. `lore.query("text", limit=3)` returns at most 3 results
5. `lore.query("text", min_confidence=0.5)` excludes lessons below threshold
6. Each result includes a `score` field (0-1 float)
7. Query on empty store returns empty list (no error)
8. Query with 1000 lessons returns in < 200ms (tested with synthetic data)
9. Results are `QueryResult` objects with `lesson` + `score` fields

## Technical Notes
- Cosine similarity: `numpy.dot(a, b) / (norm(a) * norm(b))`
- Load all candidate embeddings into numpy array for vectorized comparison
- Tag filtering: SQL `WHERE tags LIKE '%"stripe"%'` or deserialize and check in Python
- `numpy` is the only new dependency here
