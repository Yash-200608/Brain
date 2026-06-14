"""MemoryAgent — explicit memory ops (write, search, mark-complete)."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from agents.base import Agent
from agents.protocol import AgentResult, AgentStatus
from config import settings
from memory.store import ChromaMemoryStore
from memory.writer import MemoryWriter
from memory.retriever import MemoryRetriever

if TYPE_CHECKING:
    from core.context import TurnContext
    from core.task import Task

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

    def search(
        self, query: str, top_k: int | None = None, *, where: dict | None = None
    ) -> list[dict]:
        return self.retriever.search(query, top_k=top_k or settings.memory_top_k, where=where)

    def write(self, text: str, *, importance: float = 0.5, metadata: dict | None = None) -> str:
        return self.writer.write(text, importance=importance, metadata=metadata or {})

    async def run(self, task: Task, context: TurnContext) -> AgentResult:
        return await asyncio.to_thread(self._run_sync, task, context)

    def _run_sync(self, task: Task, context: TurnContext) -> AgentResult:
        """V1 ``_dispatch_memory`` semantics, relocated from the orchestrator."""
        text = (task.instruction or "").strip()
        if text.upper().startswith("COMPLETE_SUBTASK"):
            goals = context.goal_service
            ok = bool(goals and goals.complete_subtask_from_instruction(text))
            out = f"acknowledged: {text}" if ok else f"no matching goal/subtask: {text}"
            return AgentResult(status=AgentStatus.OK, output=out)
        # default: write the instruction as a memory (scoped when a service is present)
        if context.memory_service is not None:
            mid = context.memory_service.write(
                text,
                importance=0.5,
                principal=context.principal,
                session_id=context.session_id,
                origin="memory_agent",
            )
        else:
            mid = self.write(text, importance=0.5)
        return AgentResult(status=AgentStatus.OK, output=f"memory.written id={mid}")
