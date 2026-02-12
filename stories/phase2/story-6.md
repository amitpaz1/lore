# Story 6: Python RemoteStore

**Batch:** 5 | **Est:** 3-4h | **Dependencies:** Story 5

## Description

Implement `RemoteStore` in the Python SDK that implements the `Store` interface by making HTTP calls to the Lore server. The `Lore` class should accept `store="remote"` to use it. All existing SDK features (publish, query, upvote, downvote, export/import) must work through RemoteStore.

## Acceptance Criteria

1. `from lore import Lore; lore = Lore(store="remote", api_url="...", api_key="...")` creates a Lore instance with RemoteStore
2. `lore.publish(problem=..., resolution=..., tags=[...])` sends lesson to server and returns lesson ID
3. Embedding is computed client-side before sending (server receives the vector)
4. Redaction runs client-side before sending (server never sees unredacted text)
5. `lore.query("search text", tags=[...], limit=5)` returns list of Lesson objects
6. Query computes embedding client-side, sends vector to search endpoint
7. `lore.upvote(lesson_id)` and `lore.downvote(lesson_id)` work via PATCH endpoint
8. `lore.export_lessons()` and `lore.import_lessons(lessons)` work via bulk endpoints
9. Connection errors raise `LoreConnectionError` (new exception type)
10. Auth errors (401) raise `LoreAuthError` (new exception type)
11. `RemoteStore` uses `httpx.Client` with connection pooling and 30s timeout
12. All tests pass against a real server (Docker Compose in CI)

## Technical Notes

- File: `src/lore/store/remote.py`
- Add `httpx` as optional dependency: `pip install lore-memory[remote]`
- RemoteStore implements the same `Store` ABC
- The `Lore.__init__` needs a small change to accept `store="remote"` + url/key params
- Reuse existing `Lesson` type — just serialize/deserialize over HTTP
- Add new exceptions to `src/lore/exceptions.py`
