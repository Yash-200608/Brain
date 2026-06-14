"""Brain V2 model gateway — provider-agnostic LLM access (Ollama by default)."""
from .base import ModelProvider, ModelProviderError
from .gateway import ModelGateway, get_model_gateway, set_model_gateway
from .ollama import OllamaProvider

__all__ = [
    "ModelProvider",
    "ModelProviderError",
    "ModelGateway",
    "OllamaProvider",
    "get_model_gateway",
    "set_model_gateway",
]
