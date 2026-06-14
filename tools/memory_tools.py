"""Memory tools — search & write."""
from __future__ import annotations

from typing import Any

from memory.retriever import MemoryRetriever
from memory.writer import MemoryWriter
from tools.base import Tool


class MemorySearchTool(Tool):
    def __init__(self, retriever: MemoryRetriever | None = None) -> None:
        super().__init__(
            name="memory.search",
            description="Search the long-term memory store for relevant chunks.",
            input_schema={"query": "str", "top_k": "int (optional)"},
        )
        self.retriever = retriever or MemoryRetriever()

    def run(self, **kwargs: Any) -> list[dict]:
        return self.retriever.search(str(kwargs["query"]), top_k=int(kwargs.get("top_k", 8)))


class MemoryWriteTool(Tool):
    def __init__(self, writer: MemoryWriter | None = None) -> None:
        super().__init__(
            name="memory.write",
            description="Persist a piece of text into long-term memory.",
            input_schema={"text": "str", "importance": "float in [0,1]"},
        )
        self.writer = writer or MemoryWriter()

    def run(self, **kwargs: Any) -> str:
        return self.writer.write(str(kwargs["text"]), importance=float(kwargs.get("importance", 0.5)))
