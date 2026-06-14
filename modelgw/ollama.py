"""OllamaProvider — the default, local-first model backend.

Replicates the V1 ``Agent.call`` request exactly (same endpoint, payload,
timeout) so routing through the gateway is behavior-neutral.
"""
from __future__ import annotations

from typing import Any

import requests

from config import settings
from modelgw.base import ModelProvider, ModelProviderError


class OllamaProvider(ModelProvider):
    name = "ollama"

    def __init__(self, base_url: str | None = None, *, timeout: float = 120) -> None:
        self.base_url = base_url or settings.ollama_base_url
        self.timeout = timeout

    def generate(
        self,
        *,
        model: str,
        system: str,
        prompt: str,
        temperature: float = 0.2,
        options: dict[str, Any] | None = None,
    ) -> str:
        payload = {
            "model": model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, **(options or {})},
        }
        try:
            r = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
            r.raise_for_status()
            return r.json().get("response", "")
        except requests.RequestException as e:
            raise ModelProviderError(str(e)) from e
