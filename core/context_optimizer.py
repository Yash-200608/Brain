"""ContextOptimizer — builds an LLM-ready context blob from memory results.

Moved from ``orchestrator.context_optimizer`` in Brain V2; the old import
path remains available as a compatibility shim.
"""
from __future__ import annotations

from typing import Iterable


class ContextOptimizer:
    def __init__(self, max_chars: int = 6000) -> None:
        self.max_chars = max_chars

    def build(self, chunks: Iterable[dict]) -> str:
        out: list[str] = []
        used = 0
        for i, c in enumerate(chunks):
            line = f"[{i}] {c.get('text', '')}".strip()
            if used + len(line) > self.max_chars:
                break
            out.append(line)
            used += len(line) + 2
        return "\n\n".join(out)
