"""ExecutorAgent — performs the action of a planned step."""
from __future__ import annotations

from agents.base import Agent
from config import settings

EXECUTOR_SYSTEM = """You are the executor agent. Carry out the instruction precisely.
Use the supplied context. Be terse, accurate, and action-oriented.
"""


class ExecutorAgent(Agent):
    def __init__(self) -> None:
        super().__init__("executor", settings.executor_model, EXECUTOR_SYSTEM)

    def execute(self, instruction: str, context: str = "") -> str:
        prompt = f"Instruction: {instruction}\n\nContext:\n{context}"
        return self.call(prompt, temperature=0.3)
