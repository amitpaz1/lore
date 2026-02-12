# Story 7: TypeScript RemoteStore

**Batch:** 6 | **Est:** 2-3h | **Dependencies:** Story 5

## Description

Implement `RemoteStore` in the TypeScript SDK that connects to the Lore server via HTTP. Same behavior as Python RemoteStore.

## Acceptance Criteria

1. `new Lore({ store: "remote", apiUrl: "...", apiKey: "..." })` creates a Lore instance with RemoteStore
2. `lore.publish(...)` sends lesson to server, returns lesson ID
3. Embedding computed client-side (TypeScript SDK already has embedding support)
4. `lore.query(...)` sends embedding to search endpoint, returns Lesson array
5. `lore.upvote(id)` and `lore.downvote(id)` work
6. Connection errors throw `LoreConnectionError`
7. Auth errors (401) throw `LoreAuthError`
8. Uses native `fetch` (no extra HTTP dependency)
9. All existing TypeScript tests still pass
10. Integration test passes against Docker Compose server

## Technical Notes

- File: `ts/src/store/remote.ts`
- Mirror Python RemoteStore behavior exactly
- TypeScript SDK is in `ts/` directory
- Use the same API contract — request/response shapes match Python
- Add error types to `ts/src/types.ts` or new `ts/src/errors.ts`
