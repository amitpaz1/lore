"""Lore SDK — cross-agent memory library."""

from lore.exceptions import LessonNotFoundError
from lore.lore import Lore
from lore.prompt import as_prompt
from lore.types import Lesson, QueryResult

# Lazy import to avoid hard httpx dependency for local-only users
def __getattr__(name: str):
    if name == "LoreClient":
        from lore.client import LoreClient
        return LoreClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["Lore", "LoreClient", "Lesson", "QueryResult", "LessonNotFoundError", "as_prompt"]
