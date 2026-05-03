"""Planner — orchestrator-side wrapper around the PlannerAgent.

Adds plan validation, dangerous-instruction detection, and risk normalisation.
"""
from __future__ import annotations

import logging

from agents.planner import PlannerAgent
from orchestrator.task import Task

logger = logging.getLogger(__name__)

DANGEROUS_TOKENS = ("rm ", "delete", "exec", "system", "subprocess", "os.")


class Planner:
    def __init__(self, agent: PlannerAgent | None = None) -> None:
        self.agent = agent or PlannerAgent()

    def build(self, query: str, context: str = "") -> list[Task]:
        steps = self.agent.plan(query, context)
        tasks: list[Task] = []
        for step in steps:
            risk = max(int(step.get("risk", 0)), self._risk_floor(step.get("instruction", "")))
            tasks.append(
                Task(
                    agent=step["agent"],
                    instruction=step["instruction"],
                    risk=risk,
                )
            )
        return tasks

    @staticmethod
    def _risk_floor(text: str) -> int:
        low = (text or "").lower()
        return 1 if any(tok in low for tok in DANGEROUS_TOKENS) else 0
