"""Trial report builder — aggregates spine audit + legacy invocation log (M11)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from devices.audit import DispatchAudit
from trial.confirmed_classes import (
    CONFIRMED_COMMAND_CLASSES,
    normalize_skill,
    notify_or_tts_covered,
)
from trial.legacy_reader import count_legacy_by_class, read_legacy_invocations


def build_trial_report(
    audit: DispatchAudit,
    *,
    legacy_log_path: str | None = None,
    since_ts: float | None = None,
) -> dict[str, Any]:
    spine_stats = audit.trial_stats(since_ts=since_ts)
    legacy_rows = read_legacy_invocations(legacy_log_path or "", since_ts=since_ts)
    legacy_counts = count_legacy_by_class(legacy_rows, since_ts=since_ts)

    spine_success: set[str] = set(spine_stats["success_by_class"].keys())

    confirmed: dict[str, dict[str, Any]] = {}
    for cls in CONFIRMED_COMMAND_CLASSES:
        confirmed[cls] = {
            "spine_success": spine_stats["success_by_class"].get(cls, 0),
            "spine_any": spine_stats["any_by_class"].get(cls, 0),
            "legacy": legacy_counts.get(cls, 0),
        }

    notify_tts_ok = notify_or_tts_covered(spine_success)
    legacy_zero = all(
        legacy_counts.get(cls, 0) == 0 for cls in CONFIRMED_COMMAND_CLASSES
    )

    command_coverage = all(
        confirmed[cls]["spine_success"] > 0
        for cls in CONFIRMED_COMMAND_CLASSES
        if cls not in ("phone.notify", "phone.tts")
    ) and notify_tts_ok

    return {
        "generated_at": time.time(),
        "trial_window": {
            "since_ts": since_ts,
            "first_event_ts": spine_stats.get("first_ts"),
            "last_event_ts": spine_stats.get("last_ts"),
        },
        "spine": {
            "total_events": spine_stats["total"],
            "by_outcome": spine_stats["by_outcome"],
            "by_skill": spine_stats["by_skill"],
        },
        "legacy": {
            "log_path": str(Path(legacy_log_path or "").resolve()) if legacy_log_path else None,
            "log_exists": bool(legacy_log_path and Path(legacy_log_path).is_file()),
            "total_invocations": len(legacy_rows),
            "by_command_class": legacy_counts,
        },
        "confirmed_classes": confirmed,
        "criteria": {
            "command_coverage": command_coverage,
            "legacy_zero_for_covered": legacy_zero,
            "adoption_ready": legacy_zero,
            "note": (
                "Planning locus, live declarations, approval gate, kernel "
                "independence, and concurrency require live demo attestation — "
                "see docs/audits/PRIORITY-4-M11-KEYSTONE-DEMO-CHECKLIST.md"
            ),
        },
        "real_conditions": {
            "attestation_required": True,
            "sleep_wake_cycles": None,
            "broker_or_node_restart": None,
            "multi_day_continuous_uptime": None,
        },
    }


def format_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Priority #4 Trial Report",
        "",
        f"Generated: {report['generated_at']:.0f}",
        "",
        "## Spine dispatch summary",
        f"- Total audit events: {report['spine']['total_events']}",
        "",
        "### By outcome",
    ]
    for outcome, count in sorted(report["spine"]["by_outcome"].items()):
        lines.append(f"- {outcome}: {count}")
    lines.extend(["", "## Confirmed command classes", "| class | spine ok | spine any | legacy |", "|---|---:|---:|---:|"])
    for cls, row in report["confirmed_classes"].items():
        lines.append(
            f"| {cls} | {row['spine_success']} | {row['spine_any']} | {row['legacy']} |"
        )
    lines.extend(
        [
            "",
            "## Automated criteria (partial)",
            f"- Command coverage: **{report['criteria']['command_coverage']}**",
            f"- Legacy zero for covered classes: **{report['criteria']['legacy_zero_for_covered']}**",
            "",
            report["criteria"]["note"],
        ]
    )
    return "\n".join(lines) + "\n"
