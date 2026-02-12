"""Abstract embedder interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class Embedder(ABC):
    """Abstract base class for embedding engines."""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Embed a single text string. Returns a list of floats."""

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts. Returns a list of embedding vectors."""
