"""System tools — read-only info."""
from __future__ import annotations

import platform
import time
from typing import Any

from tools.base import Tool


class SystemInfoTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            name="system.info",
            description="Return basic information about the host system.",
        )

    def run(self, **_: Any) -> dict:
        return {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "time": time.time(),
        }
