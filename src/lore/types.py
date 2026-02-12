"""Core data types for Lore SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Lesson:
    """A single lesson learned by an agent."""

    id: str
    problem: str
    resolution: str
    context: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.5
    source: Optional[str] = None
    project: Optional[str] = None
    embedding: Optional[bytes] = None
    created_at: str = ""
    updated_at: str = ""
    expires_at: Optional[str] = None
    upvotes: int = 0
    downvotes: int = 0
    meta: Optional[Dict[str, Any]] = None
