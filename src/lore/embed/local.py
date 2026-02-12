"""Local embedding engine using ONNX MiniLM-L6-v2."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional
from urllib.request import urlopen, Request

import numpy as np

from lore.embed.base import Embedder

_MODEL_DIR = os.path.join(os.path.expanduser("~"), ".lore", "models")
_MODEL_NAME = "all-MiniLM-L6-v2"

# HuggingFace ONNX model files
_HF_BASE = "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/onnx"
_MODEL_FILES = {
    "model.onnx": f"{_HF_BASE}/model.onnx",
}

# Tokenizer files from the repo root
_HF_REPO = "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main"
_TOKENIZER_FILES = {
    "tokenizer.json": f"{_HF_REPO}/tokenizer.json",
    "tokenizer_config.json": f"{_HF_REPO}/tokenizer_config.json",
    "special_tokens_map.json": f"{_HF_REPO}/special_tokens_map.json",
}

_EMBEDDING_DIM = 384


def _download_file(url: str, dest: str, desc: str) -> None:
    """Download a file with progress indication."""
    req = Request(url, headers={"User-Agent": "lore-sdk/0.1"})
    response = urlopen(req, timeout=60)  # noqa: S310
    total = response.headers.get("Content-Length")
    total_bytes = int(total) if total else None

    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_path.with_suffix(".tmp")

    downloaded = 0
    chunk_size = 128 * 1024  # 128KB

    try:
        with open(tmp_path, "wb") as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                if total_bytes and sys.stderr.isatty():
                    pct = downloaded * 100 // total_bytes
                    mb_done = downloaded / (1024 * 1024)
                    mb_total = total_bytes / (1024 * 1024)
                    sys.stderr.write(
                        f"\r  {desc}: {mb_done:.1f}/{mb_total:.1f} MB ({pct}%)"
                    )
                    sys.stderr.flush()

        if sys.stderr.isatty() and total_bytes:
            sys.stderr.write("\n")

        tmp_path.rename(dest_path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def _ensure_model(model_dir: Optional[str] = None) -> str:
    """Ensure model files exist, downloading if needed. Returns model directory."""
    base = model_dir or _MODEL_DIR
    model_path = os.path.join(base, _MODEL_NAME)

    # Check if model.onnx exists as readiness marker
    onnx_path = os.path.join(model_path, "model.onnx")
    if os.path.exists(onnx_path):
        return model_path

    sys.stderr.write(
        f"Lore: downloading embedding model ({_MODEL_NAME})...\n"
    )

    all_files = {**_MODEL_FILES, **_TOKENIZER_FILES}
    for filename, url in all_files.items():
        dest = os.path.join(model_path, filename)
        if not os.path.exists(dest):
            _download_file(url, dest, filename)

    sys.stderr.write("Lore: model ready.\n")
    return model_path


def _mean_pooling(
    token_embeddings: np.ndarray, attention_mask: np.ndarray
) -> np.ndarray:
    """Mean pooling — average token embeddings weighted by attention mask."""
    mask_expanded = np.expand_dims(attention_mask, axis=-1).astype(
        token_embeddings.dtype
    )
    summed = np.sum(token_embeddings * mask_expanded, axis=1)
    counts = np.clip(np.sum(mask_expanded, axis=1), a_min=1e-9, a_max=None)
    return summed / counts


def _normalize(embeddings: np.ndarray) -> np.ndarray:
    """L2-normalize embeddings."""
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.clip(norms, a_min=1e-9, a_max=None)
    return embeddings / norms


class LocalEmbedder(Embedder):
    """Local embedding engine using ONNX MiniLM-L6-v2.

    Downloads the model on first use and caches it to ``~/.lore/models/``.
    """

    def __init__(self, model_dir: Optional[str] = None) -> None:
        self._model_dir = model_dir
        self._session = None
        self._tokenizer = None

    def _load(self) -> None:
        """Lazy-load model and tokenizer."""
        if self._session is not None:
            return

        import onnxruntime as ort  # type: ignore[import-untyped]
        from tokenizers import Tokenizer  # type: ignore[import-untyped]

        model_path = _ensure_model(self._model_dir)

        self._session = ort.InferenceSession(
            os.path.join(model_path, "model.onnx"),
            providers=["CPUExecutionProvider"],
        )
        self._tokenizer = Tokenizer.from_file(
            os.path.join(model_path, "tokenizer.json")
        )
        # MiniLM max sequence length
        self._tokenizer.enable_truncation(max_length=256)
        self._tokenizer.enable_padding(length=256)

    def embed(self, text: str) -> List[float]:
        """Embed a single text string."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts."""
        if not texts:
            return []

        self._load()
        assert self._tokenizer is not None
        assert self._session is not None

        encodings = self._tokenizer.encode_batch(texts)
        input_ids = np.array(
            [e.ids for e in encodings], dtype=np.int64
        )
        attention_mask = np.array(
            [e.attention_mask for e in encodings], dtype=np.int64
        )
        token_type_ids = np.zeros_like(input_ids)

        outputs = self._session.run(
            None,
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "token_type_ids": token_type_ids,
            },
        )

        # outputs[0] is token embeddings: (batch, seq_len, hidden_dim)
        token_embeddings = outputs[0]
        pooled = _mean_pooling(token_embeddings, attention_mask)
        normalized = _normalize(pooled)

        return [vec.tolist() for vec in normalized]
