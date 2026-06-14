"""Envelope — the versioned wire contract shared by Brain, Jarvis, Chimera and
mobile nodes.

One JSON shape for everything that crosses a boundary: WebSocket frames,
event payloads, and (future) remote agent messages.

Versioning rules:
  * ``version`` is the protocol major. Within a major, changes are
    ADDITIVE-ONLY: new envelope types and new optional payload fields.
  * Receivers must ignore unknown payload fields and unknown envelope types
    (``extra="ignore"`` enforces the field half of that contract).
  * A breaking change requires a new major and a new constant.
"""
from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

PROTOCOL_VERSION = 2


class EnvelopeType:
    """Canonical envelope ``type`` values. Namespaced, dot-separated, stable."""

    # turn lifecycle
    TURN_SUBMIT = "turn.submit"
    TURN_STARTED = "turn.started"
    TURN_TOKEN = "turn.token"
    TURN_COMPLETED = "turn.completed"
    # task lifecycle
    TASK_ASSIGN = "task.assign"
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_BLOCKED = "task.blocked"
    # memory
    MEMORY_WRITTEN = "memory.written"
    # approvals
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_DENIED = "approval.denied"
    # agents
    AGENT_EVENT = "agent.event"


class Envelope(BaseModel):
    """A single protocol message.

    ``session`` is optional: not every message belongs to a session (e.g.
    administrative or sync traffic). ``sequence`` is a per-session,
    monotonically increasing counter assigned by the sender; ``0`` means
    "unsequenced".
    """

    model_config = ConfigDict(extra="ignore")

    version: int = PROTOCOL_VERSION
    type: str = Field(..., min_length=1)
    session: str | None = None
    sequence: int = 0
    timestamp: float = Field(default_factory=time.time)
    payload: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


def make_envelope(
    type: str,  # noqa: A002 - mirrors the wire field name
    *,
    session: str | None = None,
    sequence: int = 0,
    payload: dict[str, Any] | None = None,
) -> Envelope:
    return Envelope(type=type, session=session, sequence=sequence, payload=payload or {})


def parse_envelope(data: dict[str, Any]) -> Envelope:
    """Validate an inbound message. Raises ``pydantic.ValidationError``."""
    return Envelope.model_validate(data)
