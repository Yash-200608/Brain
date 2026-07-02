"""Base agent — every agent inherits from this."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from agents.protocol import AgentResult, AgentStatus
from modelgw import ModelProviderError, get_model_gateway

if TYPE_CHECKING:
    from core.context import TurnContext
    from core.task import Task

logger = logging.getLogger(__name__)


class Agent:
    """Generic LLM-backed agent."""

    def __init__(self, name: str, model: str, system_prompt: str) -> None:
        self.name = name
        self.model = model
        self.system_prompt = system_prompt

    def call(self, prompt: str, *, temperature: float = 0.2, **kwargs: Any) -> str:
        """Generate a completion through the model gateway (Ollama by default).

        Raises ``ModelProviderError`` on failure -- it does not swallow it.
        Callers that need a specific degraded fallback (e.g. planner/critic
        already have their own empty-output handling) catch it themselves;
        the default ``run()`` below reports it honestly as AgentStatus.ERROR
        rather than returning "" indistinguishable from a real empty answer.
        """
        return get_model_gateway().generate(
            model=self.model,
            system=self.system_prompt,
            prompt=prompt,
            temperature=temperature,
            options=kwargs or None,
        )

    async def run(self, task: Task, context: TurnContext) -> AgentResult:
        """AgentProtocol entrypoint. Default: run the instruction through the LLM.

        Subclasses override to use ``context`` (memory results, working
        context, services). The sync ``call`` is offloaded so the event loop
        stays responsive.
        """
        try:
            out = await asyncio.to_thread(self.call, task.instruction)
        except ModelProviderError as e:
            logger.exception("agent %s LLM call failed: %s", self.name, e)
            return AgentResult(status=AgentStatus.ERROR, output=f"agent {self.name} failed: {e}")
        return AgentResult(status=AgentStatus.OK, output=out)

    def __repr__(self) -> str:
        return f"<Agent {self.name} model={self.model}>"
