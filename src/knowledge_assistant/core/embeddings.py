"""Embedding providers. Always local; the app must index and search offline.

Contract: `embed(texts)` returns one vector per input, in order, or raises. It never
returns a placeholder vector — the original app returned zeros on failure, which left
rows permanently unsearchable with no error surfaced.
"""

from __future__ import annotations

from typing import Protocol


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class FastEmbedEmbedder:
    """ONNX models via fastembed. First use downloads the model (~130MB for bge-small)."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", dim: int = 384, cache_dir: str | None = None):
        from fastembed import TextEmbedding  # imported lazily: slow and heavy

        self.model_name = model_name
        self.dim = dim
        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        out = [v.tolist() for v in self._model.embed(texts, batch_size=32)]
        if len(out) != len(texts):
            raise RuntimeError(f"embedder returned {len(out)} vectors for {len(texts)} inputs")
        return out

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]

