"""Typed events — the in-process vocabulary of things that happen in Brain.

Every event maps onto a protocol :class:`~protocols.Envelope` via
:meth:`Event.to_envelope`, so anything observable in-process can be streamed
to a client without translation glue.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar

from protocols import Envelope, EnvelopeType


@dataclass
class Event:
    """Base event. Subclasses set ``TYPE`` and add payload fields."""

    TYPE: ClassVar[str] = "event"

    session_id: str | None = None
    ts: float = field(default_factory=time.time)

    def payload(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("session_id", None)
        data.pop("ts", None)
        return data

    def to_envelope(self, sequence: int = 0) -> Envelope:
        return Envelope(
            type=self.TYPE,
            session=self.session_id,
            sequence=sequence,
            timestamp=self.ts,
            payload=self.payload(),
        )


# --- turn lifecycle ---

@dataclass
class TurnStarted(Event):
    TYPE: ClassVar[str] = EnvelopeType.TURN_STARTED
    user_input: str = ""


@dataclass
class TokenStreamed(Event):
    TYPE: ClassVar[str] = EnvelopeType.TURN_TOKEN
    token: str = ""


@dataclass
class TurnCompleted(Event):
    TYPE: ClassVar[str] = EnvelopeType.TURN_COMPLETED
    response: str = ""


# --- task lifecycle ---

@dataclass
class TaskStarted(Event):
    TYPE: ClassVar[str] = EnvelopeType.TASK_STARTED
    task_id: str = ""
    agent: str = ""
    instruction: str = ""


@dataclass
class TaskCompleted(Event):
    TYPE: ClassVar[str] = EnvelopeType.TASK_COMPLETED
    task_id: str = ""
    agent: str = ""
    output: str = ""


@dataclass
class TaskFailed(Event):
    TYPE: ClassVar[str] = EnvelopeType.TASK_FAILED
    task_id: str = ""
    agent: str = ""
    reason: str = ""


@dataclass
class TaskBlocked(Event):
    TYPE: ClassVar[str] = EnvelopeType.TASK_BLOCKED
    task_id: str = ""
    agent: str = ""
    instruction: str = ""


# --- memory ---

@dataclass
class MemoryWritten(Event):
    TYPE: ClassVar[str] = EnvelopeType.MEMORY_WRITTEN
    memory_id: str = ""
    user_id: str = ""
    origin: str = ""


# --- approvals ---

@dataclass
class ApprovalRequested(Event):
    TYPE: ClassVar[str] = EnvelopeType.APPROVAL_REQUESTED
    task_id: str = ""
    instruction: str = ""
    risk: int = 0


# --- agents ---

@dataclass
class AgentEvent(Event):
    TYPE: ClassVar[str] = EnvelopeType.AGENT_EVENT
    agent: str = ""
    name: str = ""
    data: dict[str, Any] = field(default_factory=dict)
