"""CLI for M11 trial report — prints markdown to stdout or writes a file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as `python scripts/trial_report.py` from repo root.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import settings
from devices.audit import DispatchAudit
from trial.report import build_trial_report, format_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Priority #4 trial report (M11)")
    parser.add_argument(
        "--legacy-log",
        default=settings.trial_legacy_log_path,
        help="Path to JARVIS legacy_invocation_log JSONL",
    )
    parser.add_argument(
        "--since",
        type=float,
        default=settings.trial_start_ts,
        help="Unix timestamp — exclude events before this",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write markdown report to this file instead of stdout",
    )
    args = parser.parse_args()

    report = build_trial_report(
        DispatchAudit(),
        legacy_log_path=args.legacy_log,
        since_ts=args.since,
    )
    md = format_markdown(report)
    if args.output:
        args.output.write_text(md, encoding="utf-8")
        print(f"written: {args.output}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
