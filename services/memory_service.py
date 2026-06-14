"""MemoryService — the only door orchestration uses to reach memory.

Adds two things over the raw agent/store path:
  * scope metadata on every write (multi-user foundation, see
    :mod:`memory.scoping`)
  * a ``memory.written`` event on the bus

Storage implementations underneath are unchanged.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from config import settings
from events import EventBus, MemoryWritten
from memory.scoping import TRUST_STANDARD, VISIBILITY_PRIVATE, apply_scope

if TYPE_CHECKING:
    from agents.memory_agent import MemoryAgent
    from identity.models import Principal

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self, memory_agent: MemoryAgent, *, bus: EventBus | None = None) -> None:
        self.memory_agent = memory_agent
        self.bus = bus

    # -- reads --
    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        principal: Principal | None = None,
        where: dict | None = None,
    ) -> list[dict]:
        """Hybrid-scored retrieval (V1 pipeline, unchanged).

        ``principal`` is accepted now so call sites are already
        identity-aware; scoped filtering switches on in a future phase.
        """
        return self.memory_agent.search(query, top_k=top_k, where=where)

    # -- writes --
    def write(
        self,
        text: str,
        *,
        importance: float = 0.5,
        metadata: dict | None = None,
        principal: Principal | None = None,
        session_id: str | None = None,
        origin: str | None = None,
        visibility: str = VISIBILITY_PRIVATE,
        trust_level: str = TRUST_STANDARD,
    ) -> str:
        user_id = principal.user_id if principal is not None else settings.default_user_id
        meta = apply_scope(
            metadata,
            user_id=user_id,
            visibility=visibility,
            session_id=session_id,
            origin=origin,
            trust_level=trust_level,
        )
        mem_id = self.memory_agent.write(text, importance=importance, metadata=meta)
        if mem_id and self.bus is not None:
            self.bus.publish(
                MemoryWritten(
                    session_id=session_id,
                    memory_id=mem_id,
                    user_id=str(meta.get("user_id", "")),
                    origin=str(meta.get("origin", "")),
                )
            )
        return mem_id
