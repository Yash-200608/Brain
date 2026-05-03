"""WorkerRegistry — lookup table from name → agent instance."""
from __future__ import annotations

from typing import Iterable

from agents.base import Agent


class WorkerRegistry:
    def __init__(self) -> None:
        self._workers: dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        self._workers[agent.name] = agent

    def get(self, name: str) -> Agent | None:
        return self._workers.get(name)

    def all(self) -> Iterable[Agent]:
        return self._workers.values()

    def names(self) -> list[str]:
        return list(self._workers)

    def __contains__(self, name: str) -> bool:
        return name in self._workers

    def __len__(self) -> int:
        return len(self._workers)
