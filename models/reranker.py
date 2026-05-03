"""Reranker — cross-encoder reranking on top of the retrieval candidates."""
from __future__ import annotations

import logging
import threading

from config import settings

logger = logging.getLogger(__name__)


class Reranker:
    _model = None
    _lock = threading.Lock()

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.reranker_model

    def _ensure_model(self):  # noqa: ANN202
        if Reranker._model is not None:
            return Reranker._model
        with Reranker._lock:
            if Reranker._model is None:
                from sentence_transformers import CrossEncoder
                logger.info("loading reranker: %s", self.model_name)
                Reranker._model = CrossEncoder(self.model_name)
        return Reranker._model

    def score(self, query: str, docs: list[str]) -> list[float]:
        if not docs:
            return []
        m = self._ensure_model()
        pairs = [(query, d) for d in docs]
        return [float(s) for s in m.predict(pairs)]
