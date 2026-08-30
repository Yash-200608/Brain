"""Read legacy-stack invocation JSONL for trial adoption measurement (M11)."""

from __future__ import annotations

import json
from pathlib import Path


def read_legacy_invocations(path: str | Path, since_ts: float | None = None) -> list[dict]:
    p = Path(path)
    if not p.is_file():
        return []
    rows: list[dict] = []
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = row.get("ts")
            if since_ts is not None and isinstance(ts, (int, float)) and ts < since_ts:
                continue
            rows.append(row)
    return rows


def count_legacy_by_class(
    rows: list[dict], since_ts: float | None = None
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        ts = row.get("ts")
        if since_ts is not None and isinstance(ts, (int, float)) and ts < since_ts:
            continue
        cls = row.get("command_class")
        if not cls:
            continue
        counts[cls] = counts.get(cls, 0) + 1
    return counts
