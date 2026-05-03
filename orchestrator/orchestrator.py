"""JarvisOrchestrator — the core engine.

Responsibilities:
  - session locking
  - plan → execute → critic → retry loop
  - memory retrieval + write-back
  - reflection trigger
"""
from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any

from agents.critic import CriticAgent
from agents.executor import ExecutorAgent
from agents.memory_agent import MemoryAgent
from agents.registry import WorkerRegistry
from agents.research import ResearchAgent
from agents.workers import build_default_registry
from config import settings
from goals.store import GoalStore
from logs.store import SessionLogStore
from memory.store import ChromaMemoryStore
from orchestrator.context_optimizer import ContextOptimizer
from orchestrator.planner import Planner
from orchestrator.router import IntentRouter
from orchestrator.task import Task, TaskStatus
from reflection.reflector import Reflector

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    history: list[dict] = field(default_factory=list)
    last_input: str = ""
    last_memory: list[dict] = field(default_factory=list)


class JarvisOrchestrator:
    def __init__(self, registry: WorkerRegistry | None = None) -> None:
        self._lock = threading.RLock()
        self.memory_store = ChromaMemoryStore()
        self.memory_agent = MemoryAgent(self.memory_store)
        self.registry = registry or build_default_registry(self.memory_agent)

        self.router = IntentRouter()
        self.planner = Planner()
        self.critic = CriticAgent()
        self.context_opt = ContextOptimizer()
        self.reflector = Reflector(self.memory_agent)

        self.goal_store = GoalStore()
        self.log_store = SessionLogStore()

        self.state = SessionState()

    # ----- public entrypoint -----
    def handle(self, user_input: str) -> dict[str, Any]:
        with self._lock:
            return self._handle_locked(user_input)

    def _handle_locked(self, user_input: str) -> dict[str, Any]:
        intent = self.router.classify(user_input)
        logger.info("intent=%s memory=%s complexity=%s",
                    intent.intent, intent.requires_memory, intent.complexity)

        # 1. Retrieve memory
        memory_results: list[dict] = []
        if intent.requires_memory:
            memory_results = self.memory_agent.search(user_input)
        context = self.context_opt.build(memory_results)

        # 2. Plan
        tasks = self.planner.build(user_input, context=context)
        if not tasks:
            tasks = [Task(agent="executor", instruction=user_input, risk=0)]

        # 3. Execute with retry
        final_output = ""
        for attempt in range(settings.max_retries + 1):
            final_output = self._run_pipeline(tasks, context)
            verdict = self.critic.review(user_input, final_output)
            if (
                verdict.get("verdict") == "ok"
                and float(verdict.get("confidence", 0)) >= settings.critic_confidence_threshold
            ):
                break
            logger.info("critic retry %d: %s", attempt + 1, verdict.get("reason"))

        # 4. Reflect & write memory
        self.reflector.reflect(user_input, final_output)

        # 5. Log
        self.log_store.append(self.state.session_id, user_input, final_output)
        self.state.history.append({"input": user_input, "output": final_output})
        self.state.last_input = user_input
        self.state.last_memory = memory_results

        return {
            "session_id": self.state.session_id,
            "response": final_output,
            "memory_used": [m.get("id") for m in memory_results],
            "tasks": [t.__dict__ for t in tasks],
        }

    # ----- internal -----
    def _run_pipeline(self, tasks: list[Task], context: str) -> str:
        outputs: list[str] = []
        for t in tasks:
            if t.risk >= 2:
                t.status = TaskStatus.BLOCKED
                outputs.append(f"[blocked: {t.instruction}]")
                continue
            agent = self.registry.get(t.agent)
            if agent is None:
                t.fail(f"unknown agent: {t.agent}")
                continue
            t.start()
            try:
                if isinstance(agent, ResearchAgent):
                    out = agent.research(t.instruction, [c.get("text", "") for c in self.state.last_memory])
                elif isinstance(agent, ExecutorAgent):
                    out = agent.execute(t.instruction, context=context)
                elif isinstance(agent, MemoryAgent):
                    out = self._dispatch_memory(t.instruction)
                else:
                    out = agent.call(t.instruction)
                t.complete(out)
                outputs.append(out)
                # feed each step's output forward as context
                context = (context + "\n\n" + out).strip()[: self.context_opt.max_chars]
            except Exception as e:  # noqa: BLE001
                logger.exception("task %s failed", t.id)
                t.fail(str(e))
        return "\n\n".join(o for o in outputs if o).strip()

    def _dispatch_memory(self, instruction: str) -> str:
        text = (instruction or "").strip()
        if text.upper().startswith("COMPLETE_SUBTASK"):
            self.goal_store.complete_subtask_from_instruction(text)
            return f"acknowledged: {text}"
        # default: write the instruction as a memory
        mid = self.memory_agent.write(text, importance=0.5)
        return f"memory.written id={mid}"
