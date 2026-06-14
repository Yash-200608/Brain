"""SessionState + SessionActor — per-session ownership of conversational state.

The actor model replaces V1's single global lock: turns within one session
are strictly serialized (same correctness property as before), while
different sessions proceed independently. Concurrency comes from caller
threads (FastAPI's threadpool, CLI thread); each turn runs the async
pipeline on a private event loop via ``asyncio.run``.

``handle_turn`` (sync) must not be called from a running event loop — async
callers use ``ahandle_turn``. Both serialize on the same lock, so mixing
modes is safe.
"""
from __future__ import annotations

import asyncio
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from identity.models import Principal


@dataclass
class SessionState:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    history: list[dict] = field(default_factory=list)
    last_input: str = ""
    last_memory: list[dict] = field(default_factory=list)


class PipelineLike(Protocol):
    """What an actor needs from a pipeline (lets tests inject fakes)."""

    async def run_turn(
        self,
        state: SessionState,
        user_input: str,
        principal: Principal | None = None,
    ) -> dict[str, Any]: ...


class SessionActor:
    """Owns one session's state; serializes its turns."""

    def __init__(self, session_id: str, pipeline: PipelineLike) -> None:
        self.session_id = session_id
        self.state = SessionState(session_id=session_id)
        self.last_used = time.time()
        self._pipeline = pipeline
        # plain Lock (not RLock): ahandle_turn acquires in a worker thread and
        # releases on the loop thread, which RLock forbids.
        self._lock = threading.Lock()

    def handle_turn(self, user_input: str, principal: Principal | None = None) -> dict[str, Any]:
        """Synchronous entrypoint (CLI, threadpool-backed API routes)."""
        with self._lock:
            self.last_used = time.time()
            return asyncio.run(self._pipeline.run_turn(self.state, user_input, principal))

    async def ahandle_turn(
        self, user_input: str, principal: Principal | None = None
    ) -> dict[str, Any]:
        """Async entrypoint for callers already inside an event loop."""
        await asyncio.to_thread(self._lock.acquire)
        try:
            self.last_used = time.time()
            return await self._pipeline.run_turn(self.state, user_input, principal)
        finally:
            self._lock.release()

    def busy(self) -> bool:
        return self._lock.locked()
