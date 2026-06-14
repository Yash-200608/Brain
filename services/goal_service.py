"""GoalService — goal operations for orchestration and the API."""
from __future__ import annotations

from goals.models import Goal, GoalStatus
from goals.store import GoalStore


class GoalService:
    def __init__(self, store: GoalStore | None = None) -> None:
        self.store = store or GoalStore()

    def list(self, status: GoalStatus | None = None) -> list[Goal]:
        return self.store.list(status)

    def get(self, goal_id: str) -> Goal | None:
        return self.store.get(goal_id)

    def upsert(self, goal: Goal) -> None:
        self.store.upsert(goal)

    def complete_subtask(self, goal_id: str, subtask_text: str) -> bool:
        return self.store.complete_subtask(goal_id, subtask_text)

    def complete_subtask_from_instruction(self, instruction: str) -> bool:
        return self.store.complete_subtask_from_instruction(instruction)
