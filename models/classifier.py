"""IntentClassifier — heuristic + LLM fallback."""
from __future__ import annotations

import json
import re

from agents.base import Agent
from config import settings

CLASSIFIER_SYSTEM = """Classify the user query.

Return ONLY a JSON object:
  {
    "intent": "coding" | "factual" | "task" | "personal",
    "requires_memory": bool,
    "complexity": "low" | "medium" | "high"
  }
"""


_HEURISTICS = [
    (re.compile(r"\b(?:def|class|function|bug|stack trace|compile|debug)\b", re.I), "coding"),
    (re.compile(r"\b(?:remember|recall|my\s+(?:name|preference))\b", re.I), "personal"),
    (re.compile(r"\b(?:do|run|execute|create|delete|update)\b", re.I), "task"),
]


class IntentClassifier(Agent):
    def __init__(self) -> None:
        super().__init__("classifier", settings.executor_model, CLASSIFIER_SYSTEM)

    def classify(self, query: str) -> dict:
        for pat, label in _HEURISTICS:
            if pat.search(query):
                return {"intent": label, "requires_memory": True,
                        "complexity": "medium" if len(query.split()) > 8 else "low"}
        # fallback: LLM
        raw = self.call(query, temperature=0.0)
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return {"intent": "factual", "requires_memory": True, "complexity": "low"}
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"intent": "factual", "requires_memory": True, "complexity": "low"}
