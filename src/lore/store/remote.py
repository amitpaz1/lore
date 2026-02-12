"""Remote HTTP store implementation."""

from __future__ import annotations

import json
import struct
from typing import Any, Dict, List, Optional

from lore.exceptions import LoreAuthError, LoreConnectionError
from lore.store.base import Store
from lore.types import Lesson

try:
    import httpx
except ImportError:
    raise ImportError(
        "httpx is required for RemoteStore. "
        "Install with: pip install lore-sdk[remote]"
    )


def _lesson_to_dict(lesson: Lesson) -> Dict[str, Any]:
    """Serialize a Lesson for the API, converting embedding bytes to float list."""
    d: Dict[str, Any] = {
        "problem": lesson.problem,
        "resolution": lesson.resolution,
        "context": lesson.context,
        "tags": lesson.tags,
        "confidence": lesson.confidence,
        "source": lesson.source,
        "project": lesson.project,
        "created_at": lesson.created_at,
        "updated_at": lesson.updated_at,
        "expires_at": lesson.expires_at,
        "upvotes": lesson.upvotes,
        "downvotes": lesson.downvotes,
        "meta": lesson.meta or {},
    }
    if lesson.embedding is not None:
        count = len(lesson.embedding) // 4
        d["embedding"] = list(struct.unpack(f"{count}f", lesson.embedding))
    else:
        d["embedding"] = []
    return d


def _response_to_lesson(data: Dict[str, Any]) -> Lesson:
    """Deserialize an API response dict to a Lesson."""
    # Server returns dates as strings (ISO) — keep as-is since Lesson uses str
    created_at = data.get("created_at", "")
    updated_at = data.get("updated_at", "")
    expires_at = data.get("expires_at")
    # Normalize datetime strings
    if created_at and not isinstance(created_at, str):
        created_at = str(created_at)
    if updated_at and not isinstance(updated_at, str):
        updated_at = str(updated_at)
    if expires_at and not isinstance(expires_at, str):
        expires_at = str(expires_at)

    return Lesson(
        id=data["id"],
        problem=data["problem"],
        resolution=data["resolution"],
        context=data.get("context"),
        tags=data.get("tags", []),
        confidence=data.get("confidence", 0.5),
        source=data.get("source"),
        project=data.get("project"),
        embedding=None,  # Server doesn't return embeddings in normal responses
        created_at=created_at,
        updated_at=updated_at,
        expires_at=expires_at,
        upvotes=data.get("upvotes", 0),
        downvotes=data.get("downvotes", 0),
        meta=data.get("meta"),
    )


class RemoteStore(Store):
    """HTTP-backed lesson store that delegates to a Lore Cloud server."""

    def __init__(self, api_url: str, api_key: str, timeout: float = 30.0) -> None:
        self._api_url = api_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Make an HTTP request with unified error handling."""
        try:
            resp = self._client.request(
                method, path, json=json_data, params=params
            )
        except httpx.ConnectError as exc:
            raise LoreConnectionError(f"Cannot connect to {self._api_url}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise LoreConnectionError(f"Request timed out: {exc}") from exc

        if resp.status_code in (401, 403):
            raise LoreAuthError(
                f"Authentication failed ({resp.status_code}): {resp.text}"
            )
        resp.raise_for_status()
        return resp

    def save(self, lesson: Lesson) -> None:
        """Save a lesson via POST /v1/lessons."""
        payload = _lesson_to_dict(lesson)
        resp = self._request("POST", "/v1/lessons", json_data=payload)
        # Server returns {"id": "..."} — we don't need to update lesson.id
        # because Lore class already set it.

    def get(self, lesson_id: str) -> Optional[Lesson]:
        """Get a lesson by ID via GET /v1/lessons/{id}."""
        try:
            resp = self._request("GET", f"/v1/lessons/{lesson_id}")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        return _response_to_lesson(resp.json())

    def list(
        self,
        project: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Lesson]:
        """List lessons via GET /v1/lessons."""
        params: Dict[str, Any] = {}
        if project is not None:
            params["project"] = project
        if limit is not None:
            params["limit"] = limit
        resp = self._request("GET", "/v1/lessons", params=params)
        data = resp.json()
        return [_response_to_lesson(item) for item in data["lessons"]]

    def update(self, lesson: Lesson) -> bool:
        """Update a lesson via PATCH /v1/lessons/{id}."""
        payload: Dict[str, Any] = {
            "confidence": lesson.confidence,
            "tags": lesson.tags,
            "upvotes": lesson.upvotes,
            "downvotes": lesson.downvotes,
            "meta": lesson.meta or {},
        }
        try:
            self._request("PATCH", f"/v1/lessons/{lesson.id}", json_data=payload)
            return True
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return False
            raise

    def delete(self, lesson_id: str) -> bool:
        """Delete a lesson via DELETE /v1/lessons/{id}."""
        try:
            self._request("DELETE", f"/v1/lessons/{lesson_id}")
            return True
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return False
            raise

    def search(
        self,
        embedding: List[float],
        tags: Optional[List[str]] = None,
        project: Optional[str] = None,
        limit: int = 5,
        min_confidence: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Search lessons via POST /v1/lessons/search.

        Returns raw dicts with 'score' field included.
        """
        payload: Dict[str, Any] = {
            "embedding": embedding,
            "limit": limit,
            "min_confidence": min_confidence,
        }
        if tags:
            payload["tags"] = tags
        if project:
            payload["project"] = project
        resp = self._request("POST", "/v1/lessons/search", json_data=payload)
        return resp.json()["lessons"]

    def export_lessons(self) -> List[Dict[str, Any]]:
        """Export lessons via POST /v1/lessons/export."""
        resp = self._request("POST", "/v1/lessons/export")
        return resp.json()["lessons"]

    def import_lessons(self, lessons: List[Dict[str, Any]]) -> int:
        """Import lessons via POST /v1/lessons/import."""
        resp = self._request("POST", "/v1/lessons/import", json_data={"lessons": lessons})
        return resp.json()["imported"]

    def upvote(self, lesson_id: str) -> None:
        """Atomic upvote via PATCH /v1/lessons/{id}."""
        try:
            self._request(
                "PATCH",
                f"/v1/lessons/{lesson_id}",
                json_data={"upvotes": "+1"},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                from lore.exceptions import LessonNotFoundError
                raise LessonNotFoundError(lesson_id) from exc
            raise

    def downvote(self, lesson_id: str) -> None:
        """Atomic downvote via PATCH /v1/lessons/{id}."""
        try:
            self._request(
                "PATCH",
                f"/v1/lessons/{lesson_id}",
                json_data={"downvotes": "+1"},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                from lore.exceptions import LessonNotFoundError
                raise LessonNotFoundError(lesson_id) from exc
            raise

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "RemoteStore":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
