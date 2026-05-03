"""PlannerAgent — converts a query into ordered, agent-assigned steps."""
from __future__ import annotations

import json
import logging
import re

from agents.base import Agent
from config import settings

logger = logging.getLogger(__name__)

PLANNER_SYSTEM = """You are the planner for Jarvis, an autonomous cognitive system.
Convert the user's query into an ordered list of executable steps.

Output ONLY a valid JSON array. No explanation, no markdown.

Each step has exactly:
  "agent"       : "research" | "executor" | "memory"
  "instruction" : string
  "risk"        : 0 (safe) | 1 (ask user) | 2 (block)
"""


class PlannerAgent(Agent):
    def __init__(self) -> None:
        super().__init__("planner", settings.planner_model, PLANNER_SYSTEM)

    def plan(self, query: str, context: str = "") -> list[dict]:
        prompt = f"User query: {query}\n\nContext:\n{context}\n\nRespond with the JSON plan."
        raw = self.call(prompt, temperature=0.1)
        return self._parse(raw)

    def _parse(self, raw: str) -> list[dict]:
        if not raw:
            return []
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            logger.warning("planner: invalid JSON: %s", raw[:120])
            return []
        return [s for s in data if self._valid(s)]

    @staticmethod
    def _valid(step: object) -> bool:
        if not isinstance(step, dict):
            return False
        return (
            step.get("agent") in {"research", "executor", "memory"}
            and isinstance(step.get("instruction"), str)
            and step.get("risk") in (0, 1, 2)
        )
