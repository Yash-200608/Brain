"""
Jarvis Brain — Entrypoint
Understand → Plan → Retrieve → Reason → Act → Learn
"""
from __future__ import annotations

import logging
import sys

from config.config import settings
from orchestrator.orchestrator import JarvisOrchestrator


def configure_logging() -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )


def run_cli() -> None:
    configure_logging()
    orch = JarvisOrchestrator()
    print("Jarvis Brain — CLI ready. Type 'exit' to quit.")
    while True:
        try:
            q = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q or q.lower() in {"exit", "quit"}:
            break
        result = orch.handle(q)
        print(f"jarvis> {result.get('response', '')}\n")


def run_api() -> None:
    import uvicorn
    uvicorn.run(
        "api.server:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "cli"
    {"cli": run_cli, "api": run_api}.get(mode, run_cli)()
