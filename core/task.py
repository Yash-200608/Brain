"""Task — internal record for a planned step.

Moved from ``orchestrator.task`` in Brain V2; the old import path remains
available as a compatibility shim.
"""
from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class Task:
    agent: str
    instruction: str
    risk: int = 0
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: TaskStatus = TaskStatus.PENDING
    output: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    def start(self) -> None:
        self.status = TaskStatus.RUNNING
        self.started_at = time.time()

    def complete(self, output: str) -> None:
        self.output = output
        self.status = TaskStatus.DONE
        self.finished_at = time.time()

    def fail(self, reason: str) -> None:
        self.output = reason
        self.status = TaskStatus.FAILED
        self.finished_at = time.time()
