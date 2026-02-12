"""Lore SDK exceptions."""


class LessonNotFoundError(Exception):
    """Raised when an operation targets a lesson ID that does not exist."""

    def __init__(self, lesson_id: str) -> None:
        self.lesson_id = lesson_id
        super().__init__(f"Lesson not found: {lesson_id}")


class LoreConnectionError(Exception):
    """Raised when the SDK cannot connect to the Lore server."""


class LoreAuthError(Exception):
    """Raised when the server rejects the API key (401/403)."""
