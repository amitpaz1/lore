"""Embedding engine for Lore SDK."""

from lore.embed.base import Embedder
from lore.embed.local import LocalEmbedder

__all__ = ["Embedder", "LocalEmbedder"]
