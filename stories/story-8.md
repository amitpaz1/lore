# Story 8: Export/Import + CLI

**Batch:** 5 | **Dependencies:** Story 2

## Description
Add JSON export/import for bulk lesson operations and a minimal CLI using `click` or `argparse`.

## Acceptance Criteria

1. `lore.export_lessons()` returns a JSON-serializable list of all lessons
2. `lore.export_lessons(path="lessons.json")` writes to file
3. `lore.import_lessons(path="lessons.json")` loads lessons, skipping duplicates (by ID)
4. Imported lessons retain original IDs, timestamps, and metadata
5. CLI command `lore publish --problem "..." --resolution "..."` publishes a lesson
6. CLI command `lore query "search text"` prints ranked results
7. CLI command `lore list` prints lessons in a table format
8. CLI command `lore export -o lessons.json` exports
9. CLI command `lore import lessons.json` imports
10. CLI uses the default store (`~/.lore/default.db`) with `--db` override option

## Technical Notes
- Use `click` for CLI (simple, well-known) or just `argparse` to avoid a dependency
- Export format: `{"version": 1, "lessons": [...]}` — include a version for future compat
- Import should handle both formats: raw list or wrapped with version
- Entry point in pyproject.toml: `[project.scripts] lore = "lore.cli:main"`
