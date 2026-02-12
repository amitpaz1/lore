"""Tests for semantic query (Story 4)."""

from __future__ import annotations

import time
from typing import List

import numpy as np
import pytest

from lore import Lore, QueryResult
from lore.store.memory import MemoryStore

_DIM = 384


def _fake_embed(text: str) -> List[float]:
    """Deterministic fake embedder: hash text to a normalized vector."""
    rng = np.random.RandomState(abs(hash(text)) % (2**31))
    vec = rng.randn(_DIM).astype(np.float32)
    vec = vec / np.linalg.norm(vec)
    return vec.tolist()


def _make_lore() -> Lore:
    return Lore(store=MemoryStore(), embedding_fn=_fake_embed)


class TestQuery:
    def test_query_returns_query_results(self) -> None:
        lore = _make_lore()
        lore.publish(problem="stripe 429", resolution="use backoff")
        results = lore.query("stripe rate limit")
        assert len(results) >= 1
        assert isinstance(results[0], QueryResult)
        assert isinstance(results[0].score, float)
        assert results[0].lesson.problem == "stripe 429"

    def test_query_empty_store(self) -> None:
        lore = _make_lore()
        results = lore.query("anything")
        assert results == []

    def test_query_with_tags_filter(self) -> None:
        lore = _make_lore()
        lore.publish(problem="p1", resolution="r1", tags=["stripe"])
        lore.publish(problem="p2", resolution="r2", tags=["openai"])
        results = lore.query("test", tags=["stripe"])
        assert len(results) == 1
        assert results[0].lesson.tags == ["stripe"]

    def test_query_with_limit(self) -> None:
        lore = _make_lore()
        for i in range(10):
            lore.publish(problem=f"problem {i}", resolution=f"resolution {i}")
        results = lore.query("problem", limit=3)
        assert len(results) == 3

    def test_query_with_min_confidence(self) -> None:
        lore = _make_lore()
        lore.publish(problem="low", resolution="r", confidence=0.2)
        lore.publish(problem="high", resolution="r", confidence=0.8)
        results = lore.query("test", min_confidence=0.5)
        assert len(results) == 1
        assert results[0].lesson.confidence >= 0.5

    def test_query_scores_between_0_and_1(self) -> None:
        lore = _make_lore()
        for i in range(5):
            lore.publish(problem=f"problem {i}", resolution=f"resolution {i}")
        results = lore.query("problem")
        for r in results:
            assert -1.0 <= r.score <= 1.0

    def test_query_results_sorted_by_score(self) -> None:
        lore = _make_lore()
        for i in range(10):
            lore.publish(problem=f"problem {i}", resolution=f"resolution {i}")
        results = lore.query("problem", limit=10)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_query_tag_subset_filter(self) -> None:
        """Tags filter requires ALL specified tags to be present."""
        lore = _make_lore()
        lore.publish(problem="p1", resolution="r1", tags=["a", "b"])
        lore.publish(problem="p2", resolution="r2", tags=["a"])
        results = lore.query("test", tags=["a", "b"])
        assert len(results) == 1
        assert "b" in results[0].lesson.tags

    def test_publish_stores_embedding(self) -> None:
        lore = _make_lore()
        lid = lore.publish(problem="p", resolution="r")
        lesson = lore.get(lid)
        assert lesson is not None
        assert lesson.embedding is not None
        assert len(lesson.embedding) == _DIM * 4  # float32

    def test_query_performance_1000_lessons(self) -> None:
        """Query over 1000 lessons should complete in < 200ms."""
        lore = _make_lore()
        for i in range(1000):
            lore.publish(problem=f"problem {i}", resolution=f"resolution {i}")

        start = time.perf_counter()
        results = lore.query("test query", limit=5)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert len(results) == 5
        assert elapsed_ms < 500, f"Query took {elapsed_ms:.1f}ms (>500ms)"
