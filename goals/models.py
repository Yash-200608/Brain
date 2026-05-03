"""Goal data model."""
from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field


class GoalStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETE = "complete"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class Subtask:
    text: str
    done: bool = False
    completed_at: float | None = None


@dataclass
class Goal:
    description: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: GoalStatus = GoalStatus.ACTIVE
    subtasks: list[Subtask] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def remaining(self) -> list[Subtask]:
        return [s for s in self.subtasks if not s.done]
