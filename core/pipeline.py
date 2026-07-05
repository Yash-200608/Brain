"""CognitivePipeline — one turn of the cognitive loop.

Understand → Plan → Retrieve → Reason → Act → Learn.

This is the V1 ``JarvisOrchestrator._handle_locked`` logic, behavior-identical,
with three structural changes:
  * agents execute through :class:`~agents.protocol.AgentProtocol`
    (``await agent.run(task, ctx)``) instead of isinstance dispatch;
  * storage is reached through the service layer, never directly;
  * lifecycle events are emitted on the :class:`~events.EventBus`.

The pipeline is stateless across turns: per-session state lives in
:class:`~core.session.SessionState` and is owned by the SessionActor.
Blocking (LLM / DB) calls are offloaded with ``asyncio.to_thread`` so the
coroutine remains loop-friendly.
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from agents.protocol import AgentStatus
from config import settings
from core.context import TurnContext
from core.context_optimizer import ContextOptimizer
from core.device_intents import map_device_intent
from core.planning import Planner
from core.routing import IntentRouter
from core.task import Task, TaskStatus
from events import (
    Event,
    EventBus,
    TaskBlocked,
    TaskCompleted,
    TaskFailed,
    TaskStarted,
    TurnCompleted,
    TurnStarted,
)

if TYPE_CHECKING:
    from agents.critic import CriticAgent
    from agents.registry import WorkerRegistry
    from core.session import SessionState
    from devices.approvals import ApprovalStore
    from devices.dispatcher import DeviceDispatcher
    from identity.models import Principal
    from reflection.reflector import Reflector
    from services import GoalService, MemoryService, SessionService

logger = logging.getLogger(__name__)


class CognitivePipeline:
    def __init__(
        self,
        *,
        registry: WorkerRegistry,
        router: IntentRouter,
        planner: Planner,
        critic: CriticAgent,
        context_opt: ContextOptimizer,
        reflector: Reflector,
        memory_service: MemoryService,
        goal_service: GoalService,
        session_service: SessionService,
        bus: EventBus | None = None,
        device_dispatcher: "DeviceDispatcher | None" = None,
        approval_store: "ApprovalStore | None" = None,
    ) -> None:
        self.registry = registry
        self.router = router
        self.planner = planner
        self.critic = critic
        self.context_opt = context_opt
        self.reflector = reflector
        self.memory_service = memory_service
        self.goal_service = goal_service
        self.session_service = session_service
        self.bus = bus
        # Priority #4 Milestone 7 -- both None means device intents are
        # simply never matched (device dispatch disabled), preserving the
        # pre-M7 pipeline exactly.
        self.device_dispatcher = device_dispatcher
        self.approval_store = approval_store

    # ----- public entrypoint -----
    async def run_turn(
        self,
        state: SessionState,
        user_input: str,
        principal: Principal | None = None,
    ) -> dict[str, Any]:
        session_id = state.session_id
        await self._emit(TurnStarted(session_id=session_id, user_input=user_input))

        # Priority #4 Milestone 7: deterministic device-intent mapping runs
        # BEFORE the LLM router/planner (frozen definition Risk R2) -- the
        # daily commands the retirement trial hinges on must not depend on
        # LLM parse luck. Non-matches fall through to the normal pipeline
        # unchanged.
        if self.device_dispatcher is not None:
            device_intent = map_device_intent(user_input)
            if device_intent is not None:
                return await self._run_device_turn(
                    state, user_input, device_intent, principal
                )

        intent = await asyncio.to_thread(self.router.classify, user_input)
        logger.info(
            "intent=%s memory=%s complexity=%s",
            intent.intent, intent.requires_memory, intent.complexity,
        )

        # 1. Retrieve memory
        memory_results: list[dict] = []
        if intent.requires_memory:
            memory_results = await asyncio.to_thread(self.memory_service.search, user_input)
        context = self.context_opt.build(memory_results)

        # 2. Plan
        tasks = await asyncio.to_thread(self.planner.build, user_input, context)
        if not tasks:
            tasks = [Task(agent="executor", instruction=user_input, risk=0)]

        # 3. Execute with retry
        final_output = ""
        for attempt in range(settings.max_retries + 1):
            final_output = await self._run_tasks(
                tasks, context, memory_results, principal=principal, session_id=session_id
            )
            verdict = await asyncio.to_thread(self.critic.review, user_input, final_output)
            try:
                confidence = float(verdict.get("confidence", 0))
            except (TypeError, ValueError):
                confidence = 0.0
            if (
                verdict.get("verdict") == "ok"
                and confidence >= settings.critic_confidence_threshold
            ):
                break
            logger.info("critic retry %d: %s", attempt + 1, verdict.get("reason"))

        # 4. Reflect & write memory
        await asyncio.to_thread(self.reflector.reflect, user_input, final_output)

        # 5. Log
        await asyncio.to_thread(self.session_service.append_turn, session_id, user_input, final_output)
        state.history.append({"input": user_input, "output": final_output})
        state.last_input = user_input
        state.last_memory = memory_results

        await self._emit(TurnCompleted(session_id=session_id, response=final_output))
        return {
            "session_id": session_id,
            "response": final_output,
            "memory_used": [m.get("id") for m in memory_results],
            "tasks": [t.__dict__ for t in tasks],
        }

    # ----- internal -----
    async def _run_device_turn(
        self,
        state: SessionState,
        user_input: str,
        device_intent,
        principal: Principal | None,
    ) -> dict[str, Any]:
        """One device-dispatch turn (Priority #4 Milestone 7).

        Three deliberate divergences from the normal turn, each load-bearing:
        * **No critic/retry loop.** The critic re-running _run_tasks would
          RE-DISPATCH the device action -- re-sending an SMS because an LLM
          wanted better prose. Device outputs are the node's truthful
          answer; they are not subject to literary review.
        * **No reflect step.** Reflection is LLM-dependent and every
          dispatch is already durably recorded in the dispatch audit trail;
          double-writing it into semantic memory adds noise, not recall.
        * **No memory retrieval / LLM planner.** The mapper already decided
          the plan deterministically.
        Session logging, history, and Turn/Task events behave exactly like
        a normal turn.
        """
        from devices.approvals import principal_key

        session_id = state.session_id
        skill, params, risk = device_intent.skill, device_intent.params, device_intent.risk

        requester = principal_key(
            principal.user_id if principal else "unknown",
            principal.client_id if principal else "unknown",
            (principal.metadata.get("key_id") if principal else None),
        )

        if risk >= 2 and self.approval_store is not None:
            # NP-7 property 2: the tier is classified HERE, before anything
            # executes; the approval is bound to this exact action instance.
            node = self.device_dispatcher.resolve_node(skill)
            approval = self.approval_store.request(
                node=node or "unresolved", skill=skill, params=params,
                risk=risk, requester=requester,
            )
            self.device_dispatcher.audit.record(
                requester=requester, node=node or "unresolved", skill=skill,
                params=params, risk=risk, outcome="approval_requested",
                approval_id=approval.id,
            )
            instruction = (
                f"device action {skill} is approval-gated (risk {risk}); "
                f"pending approval id: {approval.id}"
            )
            task = Task(agent="device", instruction=instruction, risk=risk,
                        extra={"skill": skill, "params": params, "approval_id": approval.id})
        else:
            task = Task(agent="device", instruction=f"device: {skill} {params}",
                        risk=risk, extra={"skill": skill, "params": params})

        final_output = await self._run_tasks(
            [task], "", [], principal=principal, session_id=session_id
        )

        await asyncio.to_thread(
            self.session_service.append_turn, session_id, user_input, final_output
        )
        state.history.append({"input": user_input, "output": final_output})
        state.last_input = user_input
        state.last_memory = []

        await self._emit(TurnCompleted(session_id=session_id, response=final_output))
        return {
            "session_id": session_id,
            "response": final_output,
            "memory_used": [],
            "tasks": [task.__dict__],
        }

    async def _run_tasks(
        self,
        tasks: list[Task],
        context: str,
        memory_results: list[dict],
        *,
        principal: Principal | None,
        session_id: str,
    ) -> str:
        outputs: list[str] = []
        working = context
        for t in tasks:
            if t.risk >= 2:
                t.status = TaskStatus.BLOCKED
                outputs.append(f"[blocked: {t.instruction}]")
                await self._emit(TaskBlocked(
                    session_id=session_id, task_id=t.id, agent=t.agent, instruction=t.instruction,
                ))
                continue
            agent = self.registry.get(t.agent)
            if agent is None:
                t.fail(f"unknown agent: {t.agent}")
                await self._emit(TaskFailed(
                    session_id=session_id, task_id=t.id, agent=t.agent, reason=t.output,
                ))
                continue
            t.start()
            await self._emit(TaskStarted(
                session_id=session_id, task_id=t.id, agent=t.agent, instruction=t.instruction,
            ))
            ctx = TurnContext(
                principal=principal,
                session_id=session_id,
                working_context=working,
                memory_results=memory_results,
                memory_service=self.memory_service,
                goal_service=self.goal_service,
                bus=self.bus,
            )
            try:
                result = await agent.run(t, ctx)
                if result.status == AgentStatus.ERROR:
                    t.fail(result.output or f"agent {t.agent} reported an error")
                    await self._emit(TaskFailed(
                        session_id=session_id, task_id=t.id, agent=t.agent, reason=t.output,
                    ))
                    continue
                if result.status == AgentStatus.BLOCKED:
                    t.status = TaskStatus.BLOCKED
                    outputs.append(f"[blocked: {t.instruction}]")
                    await self._emit(TaskBlocked(
                        session_id=session_id, task_id=t.id, agent=t.agent, instruction=t.instruction,
                    ))
                    continue
                out = result.output
                t.complete(out)
                outputs.append(out)
                for suggested in result.events:
                    await self._emit(suggested)
                # feed each step's output forward as context
                working = (working + "\n\n" + out).strip()[: self.context_opt.max_chars]
                await self._emit(TaskCompleted(
                    session_id=session_id, task_id=t.id, agent=t.agent, output=out,
                ))
            except Exception as e:  # noqa: BLE001 - one task must not kill the turn
                logger.exception("task %s failed", t.id)
                t.fail(str(e))
                await self._emit(TaskFailed(
                    session_id=session_id, task_id=t.id, agent=t.agent, reason=str(e),
                ))
        return "\n\n".join(o for o in outputs if o).strip()

    async def _emit(self, event: Event) -> None:
        if self.bus is None:
            return
        try:
            await self.bus.apublish(event)
        except Exception:  # noqa: BLE001 - events must never break a turn
            logger.exception("event emission failed for %s", event.TYPE)
