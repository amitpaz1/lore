"""Tests for CLI (Story 8)."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from lore.cli import build_parser, main


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


class TestCLIParsing:
    def test_publish_args(self):
        parser = build_parser()
        args = parser.parse_args(["publish", "--problem", "p", "--resolution", "r"])
        assert args.command == "publish"
        assert args.problem == "p"

    def test_query_args(self):
        parser = build_parser()
        args = parser.parse_args(["query", "search text"])
        assert args.command == "query"
        assert args.text == "search text"

    def test_list_args(self):
        parser = build_parser()
        args = parser.parse_args(["list", "--limit", "10"])
        assert args.command == "list"
        assert args.limit == 10

    def test_export_args(self):
        parser = build_parser()
        args = parser.parse_args(["export", "-o", "out.json"])
        assert args.command == "export"
        assert args.output == "out.json"

    def test_import_args(self):
        parser = build_parser()
        args = parser.parse_args(["import", "data.json"])
        assert args.command == "import"
        assert args.file == "data.json"

    def test_db_override(self):
        parser = build_parser()
        args = parser.parse_args(["--db", "/tmp/x.db", "list"])
        assert args.db == "/tmp/x.db"


class TestCLIIntegration:
    def test_publish_and_list(self, db_path, capsys):
        main(["--db", db_path, "publish", "--problem", "test prob", "--resolution", "test res"])
        out = capsys.readouterr().out.strip()
        assert len(out) == 26  # ULID length

        main(["--db", db_path, "list"])
        out = capsys.readouterr().out
        assert "test prob" in out

    def test_query(self, db_path, capsys):
        main(["--db", db_path, "publish", "--problem", "rate limiting", "--resolution", "backoff"])
        capsys.readouterr()
        main(["--db", db_path, "query", "rate limit"])
        out = capsys.readouterr().out
        assert "rate limiting" in out

    def test_export_import_roundtrip(self, db_path, tmp_path, capsys):
        main(["--db", db_path, "publish", "--problem", "p1", "--resolution", "r1"])
        capsys.readouterr()

        export_path = str(tmp_path / "export.json")
        main(["--db", db_path, "export", "-o", export_path])
        assert os.path.exists(export_path)

        db2 = str(tmp_path / "test2.db")
        main(["--db", db2, "import", export_path])
        out = capsys.readouterr().out
        assert "Imported 1" in out

    def test_export_to_stdout(self, db_path, capsys):
        main(["--db", db_path, "publish", "--problem", "p1", "--resolution", "r1"])
        capsys.readouterr()
        main(["--db", db_path, "export"])
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["version"] == 1

    def test_no_command_exits(self):
        with pytest.raises(SystemExit):
            main([])

    def test_list_empty(self, db_path, capsys):
        main(["--db", db_path, "list"])
        out = capsys.readouterr().out
        assert "No lessons" in out
