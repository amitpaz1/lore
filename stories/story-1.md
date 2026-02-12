# Story 1: Python Project Scaffolding

**Batch:** 1 | **Dependencies:** None

## Description
Set up the Python project with modern tooling: pyproject.toml, src layout, pytest, ruff, type hints. Create the package structure from architecture.md. Include a `Lesson` dataclass and the abstract `Store` interface.

## Acceptance Criteria

1. `pip install -e .` succeeds from repo root
2. `import lore` works and exposes `Lore` class (can be a stub)
3. `Lesson` dataclass exists with all fields from the schema (id, problem, resolution, context, tags, confidence, source, project, embedding, created_at, updated_at, expires_at, upvotes, downvotes, meta)
4. `Store` abstract base class defines: `save()`, `get()`, `list()`, `delete()` methods
5. `MemoryStore` (in-memory dict) implements `Store` — used for testing
6. `pytest` runs with at least one passing test (Lesson creation)
7. `ruff check` passes with zero errors
8. Package name is `lore-sdk`, import name is `lore`

## Technical Notes
- Use `pyproject.toml` with hatchling or setuptools
- Python 3.9+ compatibility
- ULID generation: use `python-ulid` or `ulid-py` package
- `Lesson.tags` is `list[str]` in Python, stored as JSON in SQLite
- Keep `__init__.py` clean — export `Lore`, `Lesson`
