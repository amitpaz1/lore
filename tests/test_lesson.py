"""Tests for Lesson dataclass."""

from lore.types import Lesson


def test_lesson_creation_minimal():
    lesson = Lesson(
        id="abc", problem="p", resolution="r",
        created_at="t", updated_at="t",
    )
    assert lesson.id == "abc"
    assert lesson.problem == "p"
    assert lesson.tags == []
    assert lesson.confidence == 0.5
    assert lesson.upvotes == 0
    assert lesson.meta is None


def test_lesson_creation_full():
    lesson = Lesson(
        id="abc",
        problem="p",
        resolution="r",
        context="ctx",
        tags=["a", "b"],
        confidence=0.9,
        source="agent-1",
        project="proj",
        embedding=b"\x00",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        expires_at="2027-01-01T00:00:00+00:00",
        upvotes=3,
        downvotes=1,
        meta={"key": "val"},
    )
    assert lesson.tags == ["a", "b"]
    assert lesson.meta == {"key": "val"}
