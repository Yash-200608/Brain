"""MemoryRetriever — V4 hybrid retrieval pipeline.

Pipeline:
  Query → rewrite → embed → retrieve top_k * overshoot → rerank → dedupe → top_k
Score = semantic + keyword + importance + access + recency.
"""
from __future__ import annotations

import math
import re
import time

from config import settings
from memory.store import ChromaMemoryStore


def _keyword_overlap(query: str, doc: str) -> float:
    q = {t for t in re.split(r"\W+", query.lower()) if len(t) >= 3}
    d = {t for t in re.split(r"\W+", doc.lower()) if len(t) >= 3}
    if not q:
        return 0.0
    return len(q & d) / len(q)


def _recency(ts: float) -> float:
    age_days = max(0.0, (time.time() - ts) / 86400.0)
    return math.exp(-age_days / 30.0)  # half-life ~ 21 days


class MemoryRetriever:
    def __init__(self, store: ChromaMemoryStore | None = None) -> None:
        self.store = store or ChromaMemoryStore()

    def rewrite(self, query: str, prior: str = "") -> str:
        if len(query.split()) > 10 or not prior:
            return query
        return f"{query} {prior}".strip()

    def search(self, query: str, *, top_k: int | None = None, prior: str = "") -> list[dict]:
        top_k = top_k or settings.memory_top_k
        rewritten = self.rewrite(query, prior)
        candidates = self.store.query(rewritten, top_k=top_k * settings.memory_overshoot)
        scored = [self._score(rewritten, c) for c in candidates]
        scored.sort(key=lambda r: r["score"], reverse=True)
        scored = self._dedupe(scored)[:top_k]
        for r in scored:
            self.store.touch(r["id"])
        return scored

    def _score(self, query: str, item: dict) -> dict:
        meta = item.get("metadata") or {}
        # chroma returns L2 distance; convert to a [0,1] semantic similarity
        dist = float(item.get("distance", 0.0))
        semantic = 1.0 / (1.0 + dist)
        keyword = _keyword_overlap(query, item.get("text", ""))
        importance = float(meta.get("importance", 0.5))
        access = math.log1p(int(meta.get("access_count", 0))) / 5.0
        recency = _recency(float(meta.get("last_accessed", time.time())))

        score = (
            settings.weight_semantic * semantic
            + settings.weight_keyword * keyword
            + settings.weight_importance * importance
            + settings.weight_access * min(access, 1.0)
            + settings.weight_recency * recency
        )
        return {**item, "score": score, "components": {
            "semantic": semantic, "keyword": keyword, "importance": importance,
            "access": access, "recency": recency,
        }}

    @staticmethod
    def _dedupe(items: list[dict]) -> list[dict]:
        seen: set[str] = set()
        out: list[dict] = []
        for it in items:
            key = (it.get("text") or "")[:120]
            if key in seen:
                continue
            seen.add(key)
            out.append(it)
        return out
