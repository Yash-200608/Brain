"""TurnContext — everything an agent may need while executing one task.

Deliberately import-light: this module sits below both ``agents`` and
``core.pipeline`` in the dependency graph, so agents can type against it
without creating cycles.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from events.bus import EventBus
    from identity.models import Principal


@dataclass
class TurnContext:
    """Per-task execution context handed to ``AgentProtocol.run``.

    ``memory_service`` / ``goal_service`` are typed loosely on purpose —
    agents depend on the *capability* (duck-typed ``write`` /
    ``complete_subtask_from_instruction``), not on the service classes.
    """

    principal: Principal | None = None
    session_id: str = ""
    working_context: str = ""
    memory_results: list[dict] = field(default_factory=list)
    memory_service: Any = None
    goal_service: Any = None
    bus: EventBus | None = None
    extra: dict[str, Any] = field(default_factory=dict)
