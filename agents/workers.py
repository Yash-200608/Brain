"""Default worker bundle — wire up the registry."""
from __future__ import annotations

from agents.executor import ExecutorAgent
from agents.memory_agent import MemoryAgent
from agents.registry import WorkerRegistry
from agents.research import ResearchAgent


def build_default_registry(memory_agent: MemoryAgent | None = None) -> WorkerRegistry:
    reg = WorkerRegistry()
    reg.register(ResearchAgent())
    reg.register(ExecutorAgent())
    reg.register(memory_agent or MemoryAgent())
    return reg
