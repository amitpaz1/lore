# Story 10: TypeScript SQLite Store + Lore Class

**Batch:** 6 | **Dependencies:** Story 9

## Description
Implement `SqliteStore` using `better-sqlite3` and the `Lore` class with publish, get, list, delete.

## Acceptance Criteria

1. `new Lore()` creates a SQLite DB at `~/.lore/default.db`
2. `new Lore({ dbPath: "./custom.db" })` uses custom path
3. `await lore.publish({ problem: "...", resolution: "..." })` returns a ULID string
4. `await lore.get(id)` returns a `Lesson` or `null`
5. `await lore.list()` returns lessons ordered by `createdAt` descending
6. `await lore.list({ project: "foo" })` filters by project
7. `await lore.delete(id)` removes the lesson
8. Same SQLite schema as Python SDK (cross-compatible DB files)
9. All CRUD operations tested with both `MemoryStore` and `SqliteStore`

## Technical Notes
- `better-sqlite3` is synchronous but fast — wrap in async interface for API consistency
- Same schema as Python: same table, same columns, same types
- This means a DB created by Python SDK can be read by TS SDK and vice versa
