"""Device data model."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Device:
    node: str
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    # None distinguishes "never reported state" from "reported an empty dict".
    state: dict | None = None
    last_state_at: float | None = None

    def is_online(self, threshold_s: float = 90.0) -> bool:
        return (time.time() - self.last_seen) < threshold_s
