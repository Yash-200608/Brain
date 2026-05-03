"""Tool — generic callable interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Tool(ABC):
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    def run(self, **kwargs: Any) -> Any: ...


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def describe(self) -> list[dict]:
        return [{"name": t.name, "description": t.description, "input": t.input_schema}
                for t in self._tools.values()]
