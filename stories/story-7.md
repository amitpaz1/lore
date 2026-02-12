# Story 7: Confidence Decay + Upvote/Downvote

**Batch:** 4 | **Dependencies:** Story 4

## Description
Implement time-based confidence decay in query scoring and add upvote/downvote methods.

## Acceptance Criteria

1. `lore.upvote(lesson_id)` increments `upvotes` by 1
2. `lore.downvote(lesson_id)` increments `downvotes` by 1
3. Query results apply decay function: `score *= confidence * time_factor * vote_factor`
4. A 60-day-old lesson scores lower than an identical 1-day-old lesson
5. A lesson with 5 upvotes scores higher than an identical lesson with 0 votes
6. A lesson with more downvotes than upvotes scores lower
7. Half-life defaults to 30 days (configurable via `Lore(decay_half_life_days=N)`)
8. Expired lessons (`expires_at < now`) are excluded from query results
9. Upvoting/downvoting a non-existent ID raises `LessonNotFoundError`

## Technical Notes
- Decay function from architecture.md: `time_factor = 0.5 ** (age_days / half_life_days)`, `vote_factor = 1 + (upvotes - downvotes) * 0.1`
- Apply decay after cosine similarity in the query pipeline
- Clamp vote_factor to minimum 0.1 (prevent negative scores from mass downvotes)
