"""Base agent — every agent inherits from this."""
from __future__ import annotations

import logging
from typing import Any

import requests

from config import settings

logger = logging.getLogger(__name__)


class Agent:
    """Generic LLM-backed agent."""

    def __init__(self, name: str, model: str, system_prompt: str) -> None:
        self.name = name
        self.model = model
        self.system_prompt = system_prompt

    def call(self, prompt: str, *, temperature: float = 0.2, **kwargs: Any) -> str:
        """Call Ollama with the given prompt."""
        url = f"{settings.ollama_base_url}/api/generate"
        payload = {
            "model": self.model,
            "system": self.system_prompt,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, **kwargs},
        }
        try:
            r = requests.post(url, json=payload, timeout=120)
            r.raise_for_status()
            return r.json().get("response", "")
        except requests.RequestException as e:
            logger.exception("agent %s LLM call failed: %s", self.name, e)
            return ""

    def __repr__(self) -> str:
        return f"<Agent {self.name} model={self.model}>"
