"""JarvisOrchestrator — V1-compatible facade over the Brain V2 core.

V1 semantics preserved exactly:
  * ``handle(user_input)`` runs the cognitive loop and returns
    ``{session_id, response, memory_used, tasks}``;
  * passing ``session_id`` switches the "current" session and stays sticky
    for subsequent calls that omit it (V1's single-state behavior);
  * ``.state`` exposes the current session's state object.

What changed underneath: the global lock and single ``SessionState`` are
gone. Turns are routed through a :class:`~core.manager.SessionManager` to
per-session actors, so distinct sessions no longer serialize each other.
New code should use ``SessionManager`` directly; this facade exists so the
CLI, the API, and existing integrations keep working unchanged.
"""
from __future__ import annotations

import uuid
from typing import Any

from agents.critic import CriticAgent
from agents.device_agent import DeviceAgent
from agents.memory_agent import MemoryAgent
from agents.registry import WorkerRegistry
from agents.workers import build_default_registry
from core.context_optimizer import ContextOptimizer
from core.manager import SessionManager
from core.pipeline import CognitivePipeline
from core.planning import Planner
from core.routing import IntentRouter
from core.session import SessionState
from devices.approvals import ApprovalStore
from devices.dispatcher import DeviceDispatcher
from events import get_event_bus
from goals.store import GoalStore
from identity import Principal, get_identity_service
from logs.store import SessionLogStore
from memory.store import ChromaMemoryStore
from reflection.reflector import Reflector
from services import GoalService, MemoryService, SessionService

__all__ = ["JarvisOrchestrator", "SessionState"]


class JarvisOrchestrator:
    def __init__(self, registry: WorkerRegistry | None = None) -> None:
        # storage + agents (same construction as V1)
        self.memory_store = ChromaMemoryStore()
        self.memory_agent = MemoryAgent(self.memory_store)
        self.registry = registry or build_default_registry(self.memory_agent)

        self.router = IntentRouter()
        self.planner = Planner()
        self.critic = CriticAgent()
        self.context_opt = ContextOptimizer()

        self.goal_store = GoalStore()
        self.log_store = SessionLogStore()

        # V2 foundation: services, events, pipeline, session manager
        self.bus = get_event_bus()
        self.identity = get_identity_service()
        self.memory_service = MemoryService(self.memory_agent, bus=self.bus)
        self.goal_service = GoalService(self.goal_store)
        self.session_service = SessionService(self.log_store)
        self.reflector = Reflector(self.memory_service)

        # Priority #4 Milestone 7: device dispatch bridge -- the DeviceAgent
        # executes low/medium-risk device plan steps over the spine; the
        # ApprovalStore holds high-risk ones for the NP-7 approval flow.
        self.device_dispatcher = DeviceDispatcher()
        self.approval_store = ApprovalStore()
        self.registry.register(DeviceAgent(self.device_dispatcher))

        self.pipeline = CognitivePipeline(
            registry=self.registry,
            router=self.router,
            planner=self.planner,
            critic=self.critic,
            context_opt=self.context_opt,
            reflector=self.reflector,
            memory_service=self.memory_service,
            goal_service=self.goal_service,
            session_service=self.session_service,
            bus=self.bus,
            device_dispatcher=self.device_dispatcher,
            approval_store=self.approval_store,
        )
        self.sessions = SessionManager(self.pipeline)

        # V1 parity: a stable default session exists from construction time.
        self._current_session_id = uuid.uuid4().hex

    # ----- V1-compatible surface -----
    @property
    def state(self) -> SessionState:
        """State of the current (sticky) session — V1's ``self.state``."""
        return self.sessions.get_or_create(self._current_session_id).state

    def handle(
        self,
        user_input: str,
        session_id: str | None = None,
        principal: Principal | None = None,
    ) -> dict[str, Any]:
        if session_id:
            self._current_session_id = session_id
        if principal is None:
            principal = self.identity.default_principal()
        return self.sessions.handle_turn(
            user_input,
            session_id=self._current_session_id,
            principal=principal,
        )
