"""AgentProtocol — the uniform async execution contract for every agent.

Replaces the V1 isinstance-dispatch in the orchestrator: each agent knows how
to map a :class:`~core.task.Task` plus a :class:`~core.context.TurnContext`
onto its own behavior and returns a structured :class:`AgentResult`.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from core.context import TurnContext
    from core.task import Task
    from events.types import Event


class AgentStatus(str, enum.Enum):
    OK = "ok"
    ERROR = "error"
    BLOCKED = "blocked"


@dataclass
class AgentResult:
    """What an agent hands back to the pipeline.

    ``events`` are suggestions the pipeline may publish on the bus; agents
    must not publish directly so that event flow stays observable in one
    place.
    """

    status: AgentStatus = AgentStatus.OK
    output: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    events: list[Event] = field(default_factory=list)


@runtime_checkable
class AgentProtocol(Protocol):
    """Anything the pipeline can execute a task on."""

    name: str

    async def run(self, task: Task, context: TurnContext) -> AgentResult: ...
