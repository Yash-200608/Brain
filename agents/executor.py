"""ExecutorAgent — performs the action of a planned step."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from agents.base import Agent
from agents.protocol import AgentResult, AgentStatus
from config import settings
from modelgw import ModelProviderError

if TYPE_CHECKING:
    from core.context import TurnContext
    from core.task import Task

EXECUTOR_SYSTEM = """You are the executor agent. Carry out the instruction precisely.
Use the supplied context. Be terse, accurate, and action-oriented.
"""


class ExecutorAgent(Agent):
    def __init__(self) -> None:
        super().__init__("executor", settings.executor_model, EXECUTOR_SYSTEM)

    def execute(self, instruction: str, context: str = "") -> str:
        prompt = f"Instruction: {instruction}\n\nContext:\n{context}"
        return self.call(prompt, temperature=0.3)

    async def run(self, task: Task, context: TurnContext) -> AgentResult:
        try:
            out = await asyncio.to_thread(self.execute, task.instruction, context.working_context)
        except ModelProviderError as e:
            return AgentResult(status=AgentStatus.ERROR, output=f"executor failed: {e}")
        return AgentResult(status=AgentStatus.OK, output=out)
