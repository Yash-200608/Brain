"""MemoryExtractor — pulls salient facts from a session for storage."""
from __future__ import annotations

import json
import re

from agents.base import Agent
from config import settings

EXTRACTOR_SYSTEM = """Extract durable facts from this exchange that are worth
remembering long-term (preferences, decisions, identities, key results).

Output ONLY a JSON array:
  [{"text": str, "importance": float in [0,1]}, ...]
"""


class MemoryExtractor(Agent):
    def __init__(self) -> None:
        super().__init__("extractor", settings.executor_model, EXTRACTOR_SYSTEM)

    def extract(self, user_input: str, response: str) -> list[dict]:
        prompt = f"USER: {user_input}\nASSISTANT: {response}"
        raw = self.call(prompt, temperature=0.0)
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
        return [
            {"text": str(d.get("text", "")).strip(),
             "importance": float(d.get("importance", 0.5))}
            for d in data if isinstance(d, dict) and d.get("text")
        ]
