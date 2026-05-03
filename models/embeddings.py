"""Embeddings — wrapper around sentence-transformers with a lazy load."""
from __future__ import annotations

import logging
import threading
from typing import Sequence

from config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider:
    _model = None
    _lock = threading.Lock()

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.embedding_model

    def _ensure_model(self):  # noqa: ANN202
        if EmbeddingProvider._model is not None:
            return EmbeddingProvider._model
        with EmbeddingProvider._lock:
            if EmbeddingProvider._model is None:
                from sentence_transformers import SentenceTransformer
                logger.info("loading embedding model: %s", self.model_name)
                EmbeddingProvider._model = SentenceTransformer(self.model_name)
        return EmbeddingProvider._model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._ensure_model()
        vecs = model.encode(list(texts), convert_to_numpy=True, normalize_embeddings=True)
        return [v.tolist() for v in vecs]
