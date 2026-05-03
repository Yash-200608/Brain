"""ModelRouter — pick the right LLM for an agent based on complexity / cost."""
from __future__ import annotations

from config import settings


class ModelRouter:
    """Maps (agent_name, complexity) → model name."""

    def __init__(self) -> None:
        self._table: dict[tuple[str, str], str] = {
            ("planner", "low"): settings.planner_model,
            ("planner", "medium"): settings.planner_model,
            ("planner", "high"): settings.planner_model,
            ("executor", "low"): settings.executor_model,
            ("executor", "medium"): settings.executor_model,
            ("executor", "high"): settings.executor_model,
            ("critic", "low"): settings.critic_model,
            ("critic", "medium"): settings.critic_model,
            ("critic", "high"): settings.critic_model,
        }

    def pick(self, agent_name: str, complexity: str = "medium") -> str:
        return self._table.get((agent_name, complexity), settings.executor_model)
