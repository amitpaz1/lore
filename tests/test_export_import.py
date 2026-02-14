"""Tests for export/import functionality (Story 8)."""

from __future__ import annotations

import json

import pytest

from lore import Lore
from lore.store.memory import MemoryStore


def _make_lore(**kw):
    return Lore(store=MemoryStore(), redact=False, **kw)


class TestExportLessons:
    def test_export_returns_list(self):
        lore = _make_lore()
        lore.publish(problem="p1", resolution="r1")
        lore.publish(problem="p2", resolution="r2")
        result = lore.export_lessons()
        assert isinstance(result, list)
        assert len(result) == 2

    def test_export_no_embedding_field(self):
        lore = _make_lore()
        lore.publish(problem="p1", resolution="r1")
        result = lore.export_lessons()
        assert "embedding" not in result[0]

    def test_export_to_file(self, tmp_path):
        lore = _make_lore()
        lore.publish(problem="p1", resolution="r1")
        path = str(tmp_path / "out.json")
        result = lore.export_lessons(path=path)
        assert len(result) == 1
        with open(path) as f:
            data = json.load(f)
        assert data["version"] == 1
        assert len(data["lessons"]) == 1

    def test_export_empty(self):
        lore = _make_lore()
        assert lore.export_lessons() == []

    def test_export_preserves_fields(self):
        lore = _make_lore()
        lore.publish(problem="prob", resolution="res", tags=["a", "b"], confidence=0.9)
        item = lore.export_lessons()[0]
        assert item["problem"] == "prob"
        assert item["resolution"] == "res"
        assert item["tags"] == ["a", "b"]
        assert item["confidence"] == 0.9


class TestImportLessons:
    def test_import_from_file(self, tmp_path):
        # Export from one instance, import into another
        lore1 = _make_lore()
        lid = lore1.publish(problem="p1", resolution="r1")
        path = str(tmp_path / "data.json")
        lore1.export_lessons(path=path)

        lore2 = _make_lore()
        count = lore2.import_lessons(path=path)
        assert count == 1
        lessons = lore2.list()
        assert len(lessons) == 1
        assert lessons[0].id == lid

    def test_import_skips_duplicates(self, tmp_path):
        lore = _make_lore()
        lore.publish(problem="p1", resolution="r1")
        path = str(tmp_path / "data.json")
        lore.export_lessons(path=path)
        # Import into same store — should skip
        count = lore.import_lessons(path=path)
        assert count == 0
        assert len(lore.list()) == 1

    def test_import_raw_list(self):
        lore = _make_lore()
        data = [
            {"id": "test-1", "problem": "p", "resolution": "r"},
            {"id": "test-2", "problem": "p2", "resolution": "r2"},
        ]
        count = lore.import_lessons(data=data)
        assert count == 2
        assert len(lore.list()) == 2

    def test_import_wrapped_format(self):
        lore = _make_lore()
        data = {
            "version": 1,
            "lessons": [{"id": "test-1", "problem": "p", "resolution": "r"}],
        }
        count = lore.import_lessons(data=data)
        assert count == 1

    def test_import_retains_original_timestamps(self, tmp_path):
        lore1 = _make_lore()
        lid = lore1.publish(problem="p", resolution="r")
        original = lore1.get(lid)
        path = str(tmp_path / "data.json")
        lore1.export_lessons(path=path)

        lore2 = _make_lore()
        lore2.import_lessons(path=path)
        imported = lore2.get(lid)
        assert imported.created_at == original.created_at

    def test_import_no_args_raises(self):
        lore = _make_lore()
        with pytest.raises(ValueError):
            lore.import_lessons()

    def test_imported_lessons_are_queryable(self):
        lore1 = _make_lore()
        lore1.publish(problem="rate limiting", resolution="use exponential backoff")
        data = lore1.export_lessons()

        lore2 = _make_lore()
        lore2.import_lessons(data=data)
        results = lore2.query("rate limit")
        assert len(results) >= 1
