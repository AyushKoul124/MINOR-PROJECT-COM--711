"""RAG Layer — Sentence Embedder.

Generates 384-dimensional dense semantic vector embeddings using
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` across
English and Indic code-mixed text.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("rag.embedder")

DEFAULT_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384


class RAGEmbedder:
    """Lazy-loaded sentence embedder for semantic search and document indexing."""

    def __init__(self, model_name: str | None = None, device: str | None = None) -> None:
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL_NAME)
        self._device_override = device
        self._model: Any = None

    @property
    def device(self) -> str:
        """Resolve target device with safe CUDA fallback."""
        if self._device_override:
            return self._device_override
        import torch
        if torch.cuda.is_available() and os.getenv("DEVICE", "").lower() == "cuda":
            return "cuda"
        return "cpu"

    def _load_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            dev = self.device
            logger.info("Loading RAG SentenceTransformer '%s' on %s...", self.model_name, dev)
            self._model = SentenceTransformer(self.model_name, device=dev)
        return self._model

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text string into a 384-dimensional dense vector."""
        model = self._load_model()
        vec = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return vec.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text strings into normalized dense vectors."""
        if not texts:
            return []
        model = self._load_model()
        vecs = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True, batch_size=32)
        return [v.tolist() for v in vecs]
