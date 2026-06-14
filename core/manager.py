"""SessionManager — routes turns to per-session actors.

Replaces the V1 global-orchestrator-lock model: N sessions run concurrently,
each internally serialized by its actor.

Eviction: when the actor table exceeds ``settings.max_sessions``, the
longest-idle non-busy actors are dropped. Their episodic log persists (the
turn store is append-only); only the in-RAM working state is released — the
same thing V1 lost on process restart. Rehydration from the log is a future
phase.
"""
from __future__ import annotations

import logging
import threading
import uuid
from typing import TYPE_CHECKING, Any

from config import settings
from core.session import PipelineLike, SessionActor

if TYPE_CHECKING:
    from identity.models import Principal

logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self, pipeline: PipelineLike, *, max_sessions: int | None = None) -> None:
        self._pipeline = pipeline
        self._max_sessions = max_sessions or settings.max_sessions
        self._actors: dict[str, SessionActor] = {}
        self._lock = threading.Lock()

    # -- actor access --
    def get_or_create(self, session_id: str | None = None) -> SessionActor:
        sid = session_id or uuid.uuid4().hex
        with self._lock:
            actor = self._actors.get(sid)
            if actor is None:
                self._evict_idle_locked()
                actor = SessionActor(sid, self._pipeline)
                self._actors[sid] = actor
            return actor

    def get(self, session_id: str) -> SessionActor | None:
        with self._lock:
            return self._actors.get(session_id)

    def session_ids(self) -> list[str]:
        with self._lock:
            return list(self._actors)

    def __len__(self) -> int:
        with self._lock:
            return len(self._actors)

    # -- turn handling --
    def handle_turn(
        self,
        user_input: str,
        *,
        session_id: str | None = None,
        principal: Principal | None = None,
    ) -> dict[str, Any]:
        return self.get_or_create(session_id).handle_turn(user_input, principal)

    async def ahandle_turn(
        self,
        user_input: str,
        *,
        session_id: str | None = None,
        principal: Principal | None = None,
    ) -> dict[str, Any]:
        return await self.get_or_create(session_id).ahandle_turn(user_input, principal)

    # -- internals --
    def _evict_idle_locked(self) -> None:
        """Caller holds ``self._lock``."""
        if len(self._actors) < self._max_sessions:
            return
        idle_first = sorted(self._actors.values(), key=lambda a: a.last_used)
        for actor in idle_first:
            if len(self._actors) < self._max_sessions:
                break
            if actor.busy():
                continue
            del self._actors[actor.session_id]
            logger.info("evicted idle session %s", actor.session_id)
