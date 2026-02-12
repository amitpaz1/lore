# Story 2: SQLite Store — Publish, Get, List, Delete

**Batch:** 1 | **Dependencies:** Story 1

## Description
Implement `SqliteStore` backed by SQLite. The `Lore` class wires up to it by default. Publish creates a lesson (without embeddings — that's Story 4), get retrieves by ID, list supports filtering, delete removes.

## Acceptance Criteria

1. `lore = Lore()` creates a SQLite DB at `~/.lore/default.db` automatically
2. `lore = Lore(db_path="./custom.db")` uses a custom path
3. `lore.publish(problem="...", resolution="...")` returns a ULID string
4. `lore.get(id)` returns a `Lesson` or `None`
5. `lore.list()` returns all lessons, ordered by `created_at` descending
6. `lore.list(project="foo")` filters by project
7. `lore.list(limit=10)` respects limit
8. `lore.delete(id)` removes the lesson; subsequent `get()` returns `None`
9. Lesson `created_at` and `updated_at` are auto-set to ISO 8601 UTC
10. All CRUD operations tested with both `MemoryStore` and `SqliteStore`

## Technical Notes
- Use Python's built-in `sqlite3` module
- Schema from architecture.md (create table on init)
- Tags stored as JSON text in SQLite
- No embedding logic yet — `embedding` column stays NULL
- `project` parameter on `Lore()` sets default project for all operations
