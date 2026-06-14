"""Embeddings — wrapper around sentence-transformers with a lazy load."""
from __future__ import annotations

import logging
import threading
from typing import Sequence

from config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider:
    # cache keyed by model name — providers with different models must not
    # silently share one loaded model
    _models: dict = {}
    _lock = threading.Lock()

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.embedding_model

    def _ensure_model(self):  # noqa: ANN202
        model = EmbeddingProvider._models.get(self.model_name)
        if model is not None:
            return model
        with EmbeddingProvider._lock:
            if self.model_name not in EmbeddingProvider._models:
                from sentence_transformers import SentenceTransformer
                logger.info("loading embedding model: %s", self.model_name)
                EmbeddingProvider._models[self.model_name] = SentenceTransformer(self.model_name)
        return EmbeddingProvider._models[self.model_name]

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._ensure_model()
        vecs = model.encode(list(texts), convert_to_numpy=True, normalize_embeddings=True)
        return [v.tolist() for v in vecs]
