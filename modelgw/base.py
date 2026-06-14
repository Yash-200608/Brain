"""Model provider contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ModelProviderError(RuntimeError):
    """Raised when a provider fails to produce a completion."""


class ModelProvider(ABC):
    """A backend capable of LLM text generation."""

    name: str = "base"

    @abstractmethod
    def generate(
        self,
        *,
        model: str,
        system: str,
        prompt: str,
        temperature: float = 0.2,
        options: dict[str, Any] | None = None,
    ) -> str:
        """Return the completion text. Raises ModelProviderError on failure."""
