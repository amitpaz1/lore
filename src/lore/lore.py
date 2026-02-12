"""Main Lore class — entry point for the SDK."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Optional

from ulid import ULID

from lore.store.base import Store
from lore.store.sqlite import SqliteStore
from lore.types import Lesson


class Lore:
    """Cross-agent memory library.

    Usage::

        lore = Lore()
        lesson_id = lore.publish(problem="...", resolution="...")
        lesson = lore.get(lesson_id)
    """

    def __init__(
        self,
        project: Optional[str] = None,
        db_path: Optional[str] = None,
        store: Optional[Store] = None,
    ) -> None:
        self.project = project
        if store is not None:
            self._store = store
        else:
            if db_path is None:
                db_path = os.path.join(
                    os.path.expanduser("~"), ".lore", "default.db"
                )
            self._store = SqliteStore(db_path)

    def close(self) -> None:
        """Close underlying store if it supports closing."""
        if hasattr(self._store, "close"):
            self._store.close()  # type: ignore[attr-defined]

    def __enter__(self) -> "Lore":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def publish(
        self,
        problem: str,
        resolution: str,
        context: Optional[str] = None,
        tags: Optional[List[str]] = None,
        confidence: float = 0.5,
        source: Optional[str] = None,
        project: Optional[str] = None,
    ) -> str:
        """Publish a new lesson. Returns the lesson ID (ULID)."""
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(
                f"confidence must be between 0.0 and 1.0, got {confidence}"
            )
        now = _utc_now_iso()
        lesson = Lesson(
            id=str(ULID()),
            problem=problem,
            resolution=resolution,
            context=context,
            tags=tags or [],
            confidence=confidence,
            source=source,
            project=project or self.project,
            created_at=now,
            updated_at=now,
        )
        self._store.save(lesson)
        return lesson.id

    def get(self, lesson_id: str) -> Optional[Lesson]:
        """Get a lesson by ID."""
        return self._store.get(lesson_id)

    def list(
        self,
        project: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Lesson]:
        """List lessons, optionally filtered by project."""
        return self._store.list(project=project, limit=limit)

    def delete(self, lesson_id: str) -> bool:
        """Delete a lesson by ID."""
        return self._store.delete(lesson_id)


def _utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()
