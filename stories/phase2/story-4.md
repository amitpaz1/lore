# Story 4: Lesson CRUD Endpoints

**Batch:** 3 | **Est:** 3-4h | **Dependencies:** Story 3

## Description

Implement REST endpoints for creating, reading, updating, deleting, and listing lessons. All operations are scoped to the authenticated org. Project-scoped keys can only access their project's lessons.

## Acceptance Criteria

1. `POST /v1/lessons` creates a lesson and returns `{"id": "..."}` with HTTP 201
2. Publish validates required fields: problem (non-empty string), resolution (non-empty string), embedding (list of 384 floats)
3. Missing/invalid fields return 422 with descriptive error
4. `GET /v1/lessons/{id}` returns the lesson as JSON (200) or 404
5. `PATCH /v1/lessons/{id}` updates allowed fields (confidence, tags, upvotes, downvotes, meta) and returns 200
6. `PATCH` with `{"upvotes": "+1"}` increments upvotes atomically (same for downvotes)
7. `DELETE /v1/lessons/{id}` returns 204 on success, 404 if not found
8. `GET /v1/lessons` returns paginated list with `limit` (default 50, max 200) and `offset` query params
9. `GET /v1/lessons?project=X` filters by project
10. Project-scoped key trying to access a lesson in another project gets 404 (not 403 — don't leak existence)
11. All returned lessons include: id, problem, resolution, context, tags, confidence, source, project, created_at, updated_at, upvotes, downvotes (but NOT embedding — too large)
12. Bulk export: `POST /v1/lessons/export` returns all lessons (with embeddings) for the org/project
13. Bulk import: `POST /v1/lessons/import` accepts array of lessons and upserts them

## Technical Notes

- Use Pydantic models for request/response validation
- Store `created_at` and `updated_at` as UTC timestamps
- For upvote/downvote increment, use SQL `SET upvotes = upvotes + 1` (atomic)
- Export/import are for migration scenarios — can be slow, no need to optimize
- Lessons are always scoped: `WHERE org_id = :org_id AND (project = :project OR :project IS NULL)`
