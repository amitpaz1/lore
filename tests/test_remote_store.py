"""Tests for RemoteStore."""

from __future__ import annotations

import json
import struct
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import httpx
import pytest

from lore.exceptions import LessonNotFoundError, LoreAuthError, LoreConnectionError
from lore.store.remote import RemoteStore, _lesson_to_dict, _response_to_lesson
from lore.types import Lesson


# ── Helpers ────────────────────────────────────────────────────────


def _make_embedding_bytes(dim: int = 384) -> bytes:
    """Create dummy embedding bytes."""
    return struct.pack(f"{dim}f", *([0.1] * dim))


def _make_lesson(**overrides: Any) -> Lesson:
    defaults = dict(
        id="test-id-1",
        problem="test problem",
        resolution="test resolution",
        context=None,
        tags=["tag1"],
        confidence=0.8,
        source="test",
        project="proj",
        embedding=_make_embedding_bytes(),
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        expires_at=None,
        upvotes=0,
        downvotes=0,
        meta=None,
    )
    defaults.update(overrides)
    return Lesson(**defaults)


def _json_response(data: Any, status_code: int = 200) -> httpx.Response:
    """Create a mock httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        json=data,
        request=httpx.Request("GET", "http://test"),
    )


# ── Unit tests for serialization ───────────────────────────────────


class TestSerialization:
    def test_lesson_to_dict_converts_embedding(self) -> None:
        lesson = _make_lesson()
        d = _lesson_to_dict(lesson)
        assert isinstance(d["embedding"], list)
        assert len(d["embedding"]) == 384
        assert abs(d["embedding"][0] - 0.1) < 1e-5

    def test_lesson_to_dict_no_embedding(self) -> None:
        lesson = _make_lesson(embedding=None)
        d = _lesson_to_dict(lesson)
        assert d["embedding"] == []

    def test_response_to_lesson(self) -> None:
        data = {
            "id": "abc",
            "problem": "p",
            "resolution": "r",
            "context": None,
            "tags": ["t"],
            "confidence": 0.9,
            "source": "s",
            "project": "proj",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "expires_at": None,
            "upvotes": 1,
            "downvotes": 0,
            "meta": {"k": "v"},
        }
        lesson = _response_to_lesson(data)
        assert lesson.id == "abc"
        assert lesson.tags == ["t"]
        assert lesson.meta == {"k": "v"}
        assert lesson.embedding is None  # server doesn't return embeddings


# ── RemoteStore tests with mocked HTTP ─────────────────────────────


class TestRemoteStore:
    def setup_method(self) -> None:
        self.store = RemoteStore(
            api_url="http://localhost:8765",
            api_key="lore_sk_test123",
        )

    def teardown_method(self) -> None:
        self.store.close()

    def test_save(self) -> None:
        lesson = _make_lesson()
        mock_resp = _json_response({"id": "test-id-1"}, 201)
        with patch.object(self.store._client, "request", return_value=mock_resp) as m:
            self.store.save(lesson)
            m.assert_called_once()
            call_kwargs = m.call_args
            assert call_kwargs[0][0] == "POST"
            assert call_kwargs[0][1] == "/v1/lessons"

    def test_get_found(self) -> None:
        resp_data = {
            "id": "abc",
            "problem": "p",
            "resolution": "r",
            "tags": [],
            "confidence": 0.5,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "upvotes": 0,
            "downvotes": 0,
        }
        mock_resp = _json_response(resp_data)
        with patch.object(self.store._client, "request", return_value=mock_resp):
            lesson = self.store.get("abc")
            assert lesson is not None
            assert lesson.id == "abc"

    def test_get_not_found(self) -> None:
        mock_resp = httpx.Response(
            status_code=404,
            json={"detail": "not found"},
            request=httpx.Request("GET", "http://test"),
        )
        with patch.object(self.store._client, "request", side_effect=httpx.HTTPStatusError("", request=mock_resp.request, response=mock_resp)):
            result = self.store.get("missing")
            assert result is None

    def test_list(self) -> None:
        resp_data = {
            "lessons": [
                {
                    "id": "a",
                    "problem": "p",
                    "resolution": "r",
                    "tags": [],
                    "confidence": 0.5,
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                    "upvotes": 0,
                    "downvotes": 0,
                },
            ],
            "total": 1,
            "limit": 50,
            "offset": 0,
        }
        mock_resp = _json_response(resp_data)
        with patch.object(self.store._client, "request", return_value=mock_resp):
            lessons = self.store.list(project="proj", limit=10)
            assert len(lessons) == 1
            assert lessons[0].id == "a"

    def test_delete_found(self) -> None:
        mock_resp = httpx.Response(
            status_code=204,
            request=httpx.Request("DELETE", "http://test"),
        )
        with patch.object(self.store._client, "request", return_value=mock_resp):
            assert self.store.delete("abc") is True

    def test_delete_not_found(self) -> None:
        mock_resp = httpx.Response(
            status_code=404,
            json={"detail": "not found"},
            request=httpx.Request("DELETE", "http://test"),
        )
        with patch.object(self.store._client, "request", side_effect=httpx.HTTPStatusError("", request=mock_resp.request, response=mock_resp)):
            assert self.store.delete("missing") is False

    def test_update(self) -> None:
        lesson = _make_lesson()
        resp_data = {
            "id": "test-id-1",
            "problem": "p",
            "resolution": "r",
            "tags": ["tag1"],
            "confidence": 0.8,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "upvotes": 0,
            "downvotes": 0,
        }
        mock_resp = _json_response(resp_data)
        with patch.object(self.store._client, "request", return_value=mock_resp):
            assert self.store.update(lesson) is True

    def test_search(self) -> None:
        resp_data = {
            "lessons": [
                {
                    "id": "a",
                    "problem": "p",
                    "resolution": "r",
                    "tags": [],
                    "confidence": 0.5,
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                    "upvotes": 0,
                    "downvotes": 0,
                    "score": 0.95,
                },
            ],
        }
        mock_resp = _json_response(resp_data)
        with patch.object(self.store._client, "request", return_value=mock_resp):
            results = self.store.search(
                embedding=[0.1] * 384,
                tags=["t"],
                limit=5,
            )
            assert len(results) == 1
            assert results[0]["score"] == 0.95

    def test_upvote(self) -> None:
        resp_data = {
            "id": "abc",
            "problem": "p",
            "resolution": "r",
            "tags": [],
            "confidence": 0.5,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "upvotes": 1,
            "downvotes": 0,
        }
        mock_resp = _json_response(resp_data)
        with patch.object(self.store._client, "request", return_value=mock_resp):
            self.store.upvote("abc")  # should not raise

    def test_upvote_not_found(self) -> None:
        mock_resp = httpx.Response(
            status_code=404,
            json={"detail": "not found"},
            request=httpx.Request("PATCH", "http://test"),
        )
        with patch.object(self.store._client, "request", side_effect=httpx.HTTPStatusError("", request=mock_resp.request, response=mock_resp)):
            with pytest.raises(LessonNotFoundError):
                self.store.upvote("missing")

    def test_downvote(self) -> None:
        resp_data = {
            "id": "abc",
            "problem": "p",
            "resolution": "r",
            "tags": [],
            "confidence": 0.5,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "upvotes": 0,
            "downvotes": 1,
        }
        mock_resp = _json_response(resp_data)
        with patch.object(self.store._client, "request", return_value=mock_resp):
            self.store.downvote("abc")

    def test_export(self) -> None:
        resp_data = {"lessons": [{"id": "a", "problem": "p", "resolution": "r"}]}
        mock_resp = _json_response(resp_data)
        with patch.object(self.store._client, "request", return_value=mock_resp):
            result = self.store.export_lessons()
            assert len(result) == 1

    def test_import(self) -> None:
        mock_resp = _json_response({"imported": 3})
        with patch.object(self.store._client, "request", return_value=mock_resp):
            count = self.store.import_lessons([{"problem": "p", "resolution": "r"}])
            assert count == 3

    def test_auth_error_401(self) -> None:
        mock_resp = httpx.Response(
            status_code=401,
            text="Unauthorized",
            request=httpx.Request("GET", "http://test"),
        )
        with patch.object(self.store._client, "request", return_value=mock_resp):
            with pytest.raises(LoreAuthError):
                self.store.get("abc")

    def test_auth_error_403(self) -> None:
        mock_resp = httpx.Response(
            status_code=403,
            text="Forbidden",
            request=httpx.Request("GET", "http://test"),
        )
        with patch.object(self.store._client, "request", return_value=mock_resp):
            with pytest.raises(LoreAuthError):
                self.store.get("abc")

    def test_connection_error(self) -> None:
        with patch.object(
            self.store._client,
            "request",
            side_effect=httpx.ConnectError("refused"),
        ):
            with pytest.raises(LoreConnectionError):
                self.store.get("abc")

    def test_timeout_error(self) -> None:
        with patch.object(
            self.store._client,
            "request",
            side_effect=httpx.ReadTimeout("timed out"),
        ):
            with pytest.raises(LoreConnectionError):
                self.store.get("abc")

    def test_context_manager(self) -> None:
        with patch.object(self.store._client, "close") as m:
            with self.store:
                pass
            m.assert_called_once()


# ── Lore integration with store="remote" ───────────────────────────


class TestLoreRemoteInit:
    def test_store_remote_requires_url_and_key(self) -> None:
        with pytest.raises(ValueError, match="api_url and api_key"):
            from lore.lore import Lore
            Lore(store="remote")

    def test_store_remote_creates_remote_store(self) -> None:
        with patch("lore.store.remote.httpx.Client"):
            from lore.lore import Lore
            lore = Lore(
                store="remote",
                api_url="http://localhost:8765",
                api_key="lore_sk_test",
                redact=False,
            )
            from lore.store.remote import RemoteStore
            assert isinstance(lore._store, RemoteStore)

    def test_store_invalid_string(self) -> None:
        with pytest.raises(ValueError, match="must be a Store instance"):
            from lore.lore import Lore
            Lore(store="invalid")  # type: ignore
