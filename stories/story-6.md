# Story 6: Prompt Helper

**Batch:** 4 | **Dependencies:** Story 4

## Description
Implement `lore.as_prompt(lessons, max_tokens=1000)` that formats query results into a string suitable for system prompt injection.

## Acceptance Criteria

1. `lore.as_prompt(lessons)` returns a formatted string with lesson problem, resolution, and confidence
2. Output includes a header like `"## Relevant Lessons"` or similar
3. Lessons are ordered by score (highest first)
4. `max_tokens` parameter truncates output (approximate: 1 token ≈ 4 chars)
5. When truncated, includes as many complete lessons as fit (no partial lessons)
6. Empty lessons list returns empty string
7. Output is clean markdown that reads well in a system prompt

## Technical Notes
- Simple string formatting — no Jinja, no templating engine
- Token counting: approximate with `len(text) // 4` — good enough for MVP
- Format per lesson: `**Problem:** ...\n**Resolution:** ...\n**Confidence:** 0.9\n`
