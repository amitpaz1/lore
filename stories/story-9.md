# Story 9: TypeScript Project Scaffolding

**Batch:** 6 | **Dependencies:** None (can reference Python SDK design)

## Description
Set up the TypeScript SDK project with modern tooling. Mirror the Python SDK's structure.

## Acceptance Criteria

1. `npm install` succeeds from the TS SDK root
2. `tsconfig.json` targets ES2020+, strict mode
3. Package name is `lore-sdk` with `Lore` as main export
4. `Lesson` type/interface matches Python's `Lesson` dataclass (all fields)
5. Abstract `Store` interface defined with `save`, `get`, `list`, `delete` methods
6. `MemoryStore` (in-memory Map) implements `Store` for testing
7. `vitest` configured and runs with at least one passing test
8. ESLint configured and passes

## Technical Notes
- Use `vitest` for testing, `tsup` or `esbuild` for bundling
- Monorepo or separate directory — recommend `packages/lore-sdk-ts/` alongside Python
- ULID: use `ulid` npm package
- All async: `publish`, `get`, `list`, `delete` return Promises
