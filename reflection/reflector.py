"""Reflector — extract durable facts from a turn and write them to memory."""
from __future__ import annotations

import logging
from typing import Protocol

from memory.extractor import MemoryExtractor
from reflection.scorer import ImportanceScorer

logger = logging.getLogger(__name__)


class MemoryWriterLike(Protocol):
    """Anything reflections can be written through (MemoryAgent, MemoryService)."""

    def write(self, text: str, *, importance: float = 0.5, metadata: dict | None = None) -> str: ...


class Reflector:
    def __init__(self, memory: MemoryWriterLike, extractor: MemoryExtractor | None = None) -> None:
        self.memory = memory
        self.extractor = extractor or MemoryExtractor()
        self.scorer = ImportanceScorer()

    def reflect(self, user_input: str, response: str) -> list[str]:
        facts = self.extractor.extract(user_input, response)
        ids: list[str] = []
        for f in facts:
            text = f.get("text", "")
            if not text:
                continue
            importance = max(self.scorer.score(text), float(f.get("importance", 0.0)))
            mid = self.memory.write(text, importance=importance, metadata={"source": "reflection"})
            if mid:
                ids.append(mid)
        logger.info("reflection wrote %d facts", len(ids))
        return ids
