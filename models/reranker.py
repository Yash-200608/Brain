"""Reranker — cross-encoder reranking on top of the retrieval candidates."""
from __future__ import annotations

import logging
import threading

from config import settings

logger = logging.getLogger(__name__)


class Reranker:
    # cache keyed by model name — rerankers with different models must not
    # silently share one loaded model
    _models: dict = {}
    _lock = threading.Lock()

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.reranker_model

    def _ensure_model(self):  # noqa: ANN202
        model = Reranker._models.get(self.model_name)
        if model is not None:
            return model
        with Reranker._lock:
            if self.model_name not in Reranker._models:
                from sentence_transformers import CrossEncoder
                logger.info("loading reranker: %s", self.model_name)
                Reranker._models[self.model_name] = CrossEncoder(self.model_name)
        return Reranker._models[self.model_name]

    def score(self, query: str, docs: list[str]) -> list[float]:
        if not docs:
            return []
        m = self._ensure_model()
        pairs = [(query, d) for d in docs]
        return [float(s) for s in m.predict(pairs)]
