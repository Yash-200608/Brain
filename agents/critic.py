"""CriticAgent — validates output, returns confidence + retry hint."""
from __future__ import annotations

import json
import re

from agents.base import Agent
from config import settings

CRITIC_SYSTEM = """You are the critic. Evaluate whether the executor's output
satisfies the user's intent.

Output ONLY a JSON object:
  {"confidence": float in [0,1], "verdict": "ok" | "retry", "reason": string}
"""


class CriticAgent(Agent):
    def __init__(self) -> None:
        super().__init__("critic", settings.critic_model, CRITIC_SYSTEM)

    def review(self, query: str, output: str) -> dict:
        prompt = f"User query: {query}\n\nOutput:\n{output}"
        raw = self.call(prompt, temperature=0.0)
        return self._parse(raw)

    @staticmethod
    def _parse(raw: str) -> dict:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return {"confidence": 0.5, "verdict": "ok", "reason": "no critic output"}
        try:
            d = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"confidence": 0.5, "verdict": "ok", "reason": "invalid JSON"}
        d.setdefault("confidence", 0.5)
        d.setdefault("verdict", "ok")
        d.setdefault("reason", "")
        try:
            d["confidence"] = max(0.0, min(1.0, float(d["confidence"])))
        except (TypeError, ValueError):
            d["confidence"] = 0.5
        if d["verdict"] not in ("ok", "retry"):
            d["verdict"] = "ok"
        return d
