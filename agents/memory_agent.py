"""MemoryAgent — explicit memory ops (write, search, mark-complete)."""
from __future__ import annotations

import logging

from agents.base import Agent
from config import settings
from memory.store import ChromaMemoryStore
from memory.writer import MemoryWriter
from memory.retriever import MemoryRetriever

logger = logging.getLogger(__name__)

MEMORY_SYSTEM = """You execute memory operations only. You never produce
free-form text for the user.
"""


class MemoryAgent(Agent):
    def __init__(self, store: ChromaMemoryStore | None = None) -> None:
        super().__init__("memory", settings.executor_model, MEMORY_SYSTEM)
        self.store = store or ChromaMemoryStore()
        self.writer = MemoryWriter(self.store)
        self.retriever = MemoryRetriever(self.store)

    def search(self, query: str, top_k: int | None = None) -> list[dict]:
        return self.retriever.search(query, top_k=top_k or settings.memory_top_k)

    def write(self, text: str, *, importance: float = 0.5, metadata: dict | None = None) -> str:
        return self.writer.write(text, importance=importance, metadata=metadata or {})
