"""ImportanceScorer — assigns importance to facts before they go into memory."""
from __future__ import annotations

import re

KEYWORDS_HIGH = (
    "remember", "always", "never", "prefer", "deadline", "decision", "owner", "important"
)
KEYWORDS_LOW = ("maybe", "probably", "thinking", "wonder", "joke")


class ImportanceScorer:
    def score(self, text: str) -> float:
        t = (text or "").lower()
        if not t.strip():
            return 0.0
        s = 0.5
        if any(k in t for k in KEYWORDS_HIGH):
            s += 0.3
        if any(k in t for k in KEYWORDS_LOW):
            s -= 0.2
        # numbers / dates → factual
        if re.search(r"\b(?:\d{4}|\d{1,2}/\d{1,2}|\$\d+)\b", t):
            s += 0.1
        return max(0.0, min(1.0, s))
