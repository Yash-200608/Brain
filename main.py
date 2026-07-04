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
    import asyncio
    import sys

    import uvicorn

    # aiomqtt (mqtt/client.py, Priority #3 Milestone 2) needs
    # add_reader()/add_writer(), which ProactorEventLoop -- asyncio's
    # Windows default since 3.8 -- does not implement (raises
    # NotImplementedError). SelectorEventLoop does.
    #
    # Setting asyncio.set_event_loop_policy() has NO effect here: uvicorn's
    # own asyncio_loop_factory() (uvicorn/loops/asyncio.py) hardcodes
    # `return asyncio.ProactorEventLoop` on win32 whenever use_subprocess is
    # False, and passes that factory straight to `asyncio.run(...,
    # loop_factory=...)` -- bypassing the global policy entirely (confirmed
    # by reading uvicorn 0.49.0's source directly). The fix has to happen at
    # uvicorn's own `loop=` config knob, which accepts a bare factory
    # callable (uvicorn.importer.import_from_string returns non-str values
    # unchanged), not just the "auto"/"asyncio"/"uvloop" string presets.
    #
    # This only matters once MQTT is actually enabled against a real broker
    # (Milestone 12); every earlier milestone's tests fake aiomqtt.Client()
    # entirely, so this gap was invisible until the first real live-broker
    # run. Brain has no asyncio subprocess usage anywhere (confirmed), so
    # SelectorEventLoop's lack of subprocess support on Windows is a
    # non-issue here.
    loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else "auto"

    uvicorn.run(
        "api.server:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        loop=loop_factory,
    )


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "cli"
    {"cli": run_cli, "api": run_api}.get(mode, run_cli)()
