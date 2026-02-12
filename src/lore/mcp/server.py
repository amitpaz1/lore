"""MCP server that wraps the Lore SDK.

Exposes four tools over stdio transport:
  - save_lesson: persist a lesson learned
  - recall_lessons: semantic search for relevant lessons
  - upvote_lesson: signal a lesson was helpful
  - downvote_lesson: signal a lesson was unhelpful

Configure via environment variables:
  LORE_STORE   — "local" (default) or "remote"
  LORE_PROJECT — default project scope
  LORE_API_URL — required when LORE_STORE=remote
  LORE_API_KEY — required when LORE_STORE=remote
"""

from __future__ import annotations

import os
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

from lore.lore import Lore

# ---------------------------------------------------------------------------
# Lore instance (created lazily so import doesn't trigger side-effects)
# ---------------------------------------------------------------------------

_lore: Optional[Lore] = None


def _get_lore() -> Lore:
    """Return the module-level Lore instance, creating it on first call."""
    global _lore
    if _lore is not None:
        return _lore

    store_type = os.environ.get("LORE_STORE", "local").lower()
    project = os.environ.get("LORE_PROJECT") or None

    if store_type == "remote":
        api_url = os.environ.get("LORE_API_URL")
        api_key = os.environ.get("LORE_API_KEY")
        if not api_url or not api_key:
            raise RuntimeError(
                "LORE_API_URL and LORE_API_KEY must be set when LORE_STORE=remote"
            )
        _lore = Lore(project=project, store="remote", api_url=api_url, api_key=api_key)
    else:
        _lore = Lore(project=project)

    return _lore


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="lore",
    instructions=(
        "Lore is a cross-agent memory system. Use it to save lessons learned "
        "from solving problems and to recall relevant lessons when facing new "
        "problems. This helps avoid repeating mistakes and surfaces solutions "
        "that worked before."
    ),
)


@mcp.tool(
    description=(
        "Save a lesson learned from solving a problem. "
        "USE THIS WHEN: you just solved a tricky bug, found a non-obvious fix, "
        "discovered a workaround, or learned something that future agents (or "
        "your future self) would benefit from knowing. "
        "DO NOT save trivial things — only save lessons that would save someone "
        "real time or prevent a real mistake. "
        "The problem should describe WHAT went wrong or was confusing. "
        "The resolution should describe WHAT fixed it and WHY it works."
    ),
)
def save_lesson(
    problem: str,
    resolution: str,
    context: Optional[str] = None,
    tags: Optional[List[str]] = None,
    project: Optional[str] = None,
) -> str:
    """Save a lesson to Lore memory."""
    try:
        lore = _get_lore()
        lesson_id = lore.publish(
            problem=problem,
            resolution=resolution,
            context=context,
            tags=tags,
            project=project,
        )
        return f"✅ Lesson saved (ID: {lesson_id})"
    except Exception as e:
        return f"❌ Failed to save lesson: {e}"


@mcp.tool(
    description=(
        "Search for relevant lessons from past experience. "
        "USE THIS WHEN: you're about to solve a problem, debug an error, "
        "or make a design decision — especially if you suspect someone has "
        "hit this before. Search with a natural-language description of "
        "your problem or question. "
        "GOOD queries: 'CORS errors with FastAPI', 'Docker build fails on M1', "
        "'rate limiting strategy for API'. "
        "BAD queries: 'help', 'error', 'fix this'. Be specific."
    ),
)
def recall_lessons(
    query: str,
    tags: Optional[List[str]] = None,
    limit: int = 5,
) -> str:
    """Search Lore memory for relevant lessons."""
    try:
        lore = _get_lore()
        limit = max(1, min(limit, 20))
        results = lore.query(text=query, tags=tags, limit=limit)
        if not results:
            return "No relevant lessons found. Try a different query or broader terms."

        lines: List[str] = [f"Found {len(results)} relevant lesson(s):\n"]
        for i, r in enumerate(results, 1):
            lesson = r.lesson
            lines.append(f"{'─' * 60}")
            lines.append(f"Lesson {i}  (score: {r.score:.2f}, id: {lesson.id})")
            lines.append(f"Problem:    {lesson.problem}")
            lines.append(f"Resolution: {lesson.resolution}")
            if lesson.context:
                lines.append(f"Context:    {lesson.context}")
            if lesson.tags:
                lines.append(f"Tags:       {', '.join(lesson.tags)}")
            if lesson.project:
                lines.append(f"Project:    {lesson.project}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"❌ Failed to recall lessons: {e}"


@mcp.tool(
    description=(
        "Upvote a lesson that was helpful. "
        "USE THIS WHEN: you recalled a lesson and it actually helped solve "
        "your problem. This boosts the lesson's ranking in future searches. "
        "Pass the lesson ID from recall_lessons output."
    ),
)
def upvote_lesson(lesson_id: str) -> str:
    """Upvote a lesson to boost its ranking."""
    try:
        lore = _get_lore()
        lore.upvote(lesson_id)
        return f"👍 Upvoted lesson {lesson_id}"
    except Exception as e:
        return f"❌ Failed to upvote: {e}"


@mcp.tool(
    description=(
        "Downvote a lesson that was wrong or unhelpful. "
        "USE THIS WHEN: you recalled a lesson but it was outdated, incorrect, "
        "or misleading. This lowers the lesson's ranking so others don't waste "
        "time on bad advice. Pass the lesson ID from recall_lessons output."
    ),
)
def downvote_lesson(lesson_id: str) -> str:
    """Downvote a lesson to lower its ranking."""
    try:
        lore = _get_lore()
        lore.downvote(lesson_id)
        return f"👎 Downvoted lesson {lesson_id}"
    except Exception as e:
        return f"❌ Failed to downvote: {e}"


def run_server() -> None:
    """Start the MCP server with stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()
