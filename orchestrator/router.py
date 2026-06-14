"""Compatibility shim — IntentRouter moved to ``core.routing`` in Brain V2."""
from core.routing import Intent, IntentRouter

__all__ = ["Intent", "IntentRouter"]
