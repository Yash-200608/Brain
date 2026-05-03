"""MemoryWriter — write path with importance scoring + metadata."""
from __future__ import annotations

import logging

from memory.store import ChromaMemoryStore

logger = logging.getLogger(__name__)


class MemoryWriter:
    def __init__(self, store: ChromaMemoryStore | None = None) -> None:
        self.store = store or ChromaMemoryStore()

    def write(self, text: str, *, importance: float = 0.5, metadata: dict | None = None) -> str:
        text = (text or "").strip()
        if not text:
            return ""
        importance = max(0.0, min(1.0, float(importance)))
        mem_id = self.store.add(text, importance=importance, metadata=metadata or {})
        logger.info("memory.write id=%s importance=%.2f", mem_id, importance)
        return mem_id
