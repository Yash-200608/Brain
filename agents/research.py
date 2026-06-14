"""ResearchAgent — synthesises retrieved context for downstream agents."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from agents.base import Agent
from agents.protocol import AgentResult, AgentStatus
from config import settings

if TYPE_CHECKING:
    from core.context import TurnContext
    from core.task import Task

RESEARCH_SYSTEM = """You are the research agent. Given retrieved memory chunks
and the user query, produce a concise factual brief that can ground the executor.
Cite which memory chunks (by index) you used.
"""


class ResearchAgent(Agent):
    def __init__(self) -> None:
        super().__init__("research", settings.executor_model, RESEARCH_SYSTEM)

    def research(self, instruction: str, memory_chunks: list[str]) -> str:
        formatted = "\n\n".join(f"[{i}] {c}" for i, c in enumerate(memory_chunks))
        prompt = f"Instruction: {instruction}\n\nMemory:\n{formatted}"
        return self.call(prompt, temperature=0.2)

    async def run(self, task: Task, context: TurnContext) -> AgentResult:
        chunks = [c.get("text", "") for c in context.memory_results]
        out = await asyncio.to_thread(self.research, task.instruction, chunks)
        return AgentResult(status=AgentStatus.OK, output=out)
