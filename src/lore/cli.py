"""Minimal CLI for Lore SDK using argparse."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional, Sequence


def _get_lore(db: Optional[str] = None) -> "Lore":  # noqa: F821
    from lore import Lore

    kwargs = {}
    if db:
        kwargs["db_path"] = db
    return Lore(**kwargs)


def cmd_publish(args: argparse.Namespace) -> None:
    lore = _get_lore(args.db)
    tags: List[str] = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []
    lid = lore.publish(
        problem=args.problem,
        resolution=args.resolution,
        context=args.context,
        tags=tags,
        confidence=args.confidence,
        source=args.source,
    )
    lore.close()
    print(lid)


def cmd_query(args: argparse.Namespace) -> None:
    lore = _get_lore(args.db)
    results = lore.query(args.text, limit=args.limit)
    lore.close()
    if not results:
        print("No results.")
        return
    for r in results:
        print(f"[{r.score:.3f}] {r.lesson.id}")
        print(f"  Problem:    {r.lesson.problem}")
        print(f"  Resolution: {r.lesson.resolution}")
        print()


def cmd_list(args: argparse.Namespace) -> None:
    lore = _get_lore(args.db)
    lessons = lore.list(limit=args.limit)
    lore.close()
    if not lessons:
        print("No lessons.")
        return
    # Simple table
    print(f"{'ID':<28} {'Problem':<50} {'Resolution':<50}")
    print("-" * 80)
    for l in lessons:
        print(f"{l.id:<28} {l.problem[:50]:<50} {l.resolution[:50]:<50}")


def cmd_export(args: argparse.Namespace) -> None:
    lore = _get_lore(args.db)
    lessons = lore.export_lessons(path=args.output)
    lore.close()
    if args.output:
        print(f"Exported {len(lessons)} lessons to {args.output}")
    else:
        payload = {"version": 1, "lessons": lessons}
        print(json.dumps(payload, indent=2, ensure_ascii=False))


def cmd_import(args: argparse.Namespace) -> None:
    lore = _get_lore(args.db)
    count = lore.import_lessons(path=args.file)
    lore.close()
    print(f"Imported {count} lessons from {args.file}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lore",
        description="Lore SDK — cross-agent memory CLI",
    )
    parser.add_argument("--db", default=None, help="Path to SQLite database")

    sub = parser.add_subparsers(dest="command")

    # publish
    p = sub.add_parser("publish", help="Publish a new lesson")
    p.add_argument("--problem", required=True)
    p.add_argument("--resolution", required=True)
    p.add_argument("--context", default=None)
    p.add_argument("--tags", default=None, help="Comma-separated tags")
    p.add_argument("--confidence", type=float, default=0.5)
    p.add_argument("--source", default=None)

    # query
    p = sub.add_parser("query", help="Query lessons")
    p.add_argument("text", help="Search text")
    p.add_argument("--limit", type=int, default=5)

    # list
    p = sub.add_parser("list", help="List lessons")
    p.add_argument("--limit", type=int, default=None)

    # export
    p = sub.add_parser("export", help="Export lessons to JSON")
    p.add_argument("-o", "--output", default=None, help="Output file path")

    # import
    p = sub.add_parser("import", help="Import lessons from JSON")
    p.add_argument("file", help="JSON file to import")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    handlers = {
        "publish": cmd_publish,
        "query": cmd_query,
        "list": cmd_list,
        "export": cmd_export,
        "import": cmd_import,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
