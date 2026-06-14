"""ModelGateway — single entry point for all LLM generation.

Local-first: the default (and only built-in) provider is Ollama. Future
providers (hosted LLM fallback) register here; nothing above this layer
knows which backend served a completion.
"""
from __future__ import annotations

import threading
from typing import Any

from config import settings
from modelgw.base import ModelProvider, ModelProviderError
from modelgw.ollama import OllamaProvider


class ModelGateway:
    def __init__(
        self,
        providers: dict[str, ModelProvider] | None = None,
        *,
        default: str | None = None,
    ) -> None:
        self._providers: dict[str, ModelProvider] = providers or {"ollama": OllamaProvider()}
        self._default = default or settings.llm_provider

    def register(self, provider: ModelProvider) -> None:
        self._providers[provider.name] = provider

    def provider(self, name: str | None = None) -> ModelProvider:
        key = name or self._default
        try:
            return self._providers[key]
        except KeyError:
            raise ModelProviderError(f"unknown model provider: {key}") from None

    def generate(
        self,
        *,
        model: str,
        system: str,
        prompt: str,
        temperature: float = 0.2,
        options: dict[str, Any] | None = None,
        provider: str | None = None,
    ) -> str:
        return self.provider(provider).generate(
            model=model,
            system=system,
            prompt=prompt,
            temperature=temperature,
            options=options,
        )


_gateway: ModelGateway | None = None
_gateway_lock = threading.Lock()


def get_model_gateway() -> ModelGateway:
    global _gateway
    if _gateway is None:
        with _gateway_lock:
            if _gateway is None:
                _gateway = ModelGateway()
    return _gateway


def set_model_gateway(gateway: ModelGateway | None) -> None:
    """Replace the default gateway (primarily for tests)."""
    global _gateway
    with _gateway_lock:
        _gateway = gateway
