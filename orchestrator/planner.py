"""Compatibility shim — Planner moved to ``core.planning`` in Brain V2."""
from core.planning import DANGEROUS_TOKENS, Planner

__all__ = ["DANGEROUS_TOKENS", "Planner"]
