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
        """Generate a completion through the model gateway (Ollama by default)."""
        try:
            return get_model_gateway().generate(
                model=self.model,
                system=self.system_prompt,
                prompt=prompt,
                temperature=temperature,
                options=kwargs or None,
            )
        except ModelProviderError as e:
            logger.exception("agent %s LLM call failed: %s", self.name, e)
            return ""

    async def run(self, task: Task, context: TurnContext) -> AgentResult:
        """AgentProtocol entrypoint. Default: run the instruction through the LLM.

        Subclasses override to use ``context`` (memory results, working
        context, services). The sync ``call`` is offloaded so the event loop
        stays responsive.
        """
        out = await asyncio.to_thread(self.call, task.instruction)
        return AgentResult(status=AgentStatus.OK, output=out)

    def __repr__(self) -> str:
        return f"<Agent {self.name} model={self.model}>"
