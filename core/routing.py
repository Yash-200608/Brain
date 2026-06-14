"""IntentRouter — query understanding layer.

Moved from ``orchestrator.router`` in Brain V2; the old import path remains
available as a compatibility shim.
"""
from __future__ import annotations

from dataclasses import dataclass

from models.classifier import IntentClassifier


@dataclass
class Intent:
    intent: str             # coding | factual | task | personal
    requires_memory: bool
    complexity: str         # low | medium | high


class IntentRouter:
    def __init__(self) -> None:
        self.classifier = IntentClassifier()

    def classify(self, query: str) -> Intent:
        result = self.classifier.classify(query)
        return Intent(
            intent=result.get("intent", "factual"),
            requires_memory=bool(result.get("requires_memory", True)),
            complexity=result.get("complexity", "medium"),
        )
