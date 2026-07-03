#!/usr/bin/env python3
"""Vendors Brain/protocols/chimera_contract.py into a JARVIS node SDK
checkout as a generated, do-not-edit copy.

Brain is the sole canonical owner of the Chimera wire contract (ADR-013).
JARVIS must never hand-edit its own copy -- regenerate it here instead
whenever the canonical module changes.

Usage (run from the Brain repo root):
    python scripts/sync_chimera_contract.py --jarvis-root ../JARVIS
    python scripts/sync_chimera_contract.py --jarvis-root C:\\path\\to\\JARVIS --check

--check: verify the vendored copy is up to date (compares a stamped content
         hash against the live canonical source) without writing; exits
         non-zero if stale. Useful as a manual pre-commit sanity step -- NOT
         wired into any CI/automation (none exists in this project yet).
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE = REPO_ROOT / "protocols" / "chimera_contract.py"
# Not underscore-prefixed: this is the canonical vendored *contract*, not a
# private implementation detail -- Python's leading-underscore convention
# means the latter, which would undersell what this file actually is. The
# AUTO-GENERATED / DO NOT EDIT banner in the header carries the "don't touch
# this by hand" signal instead.
VENDORED_RELPATH = Path("jarvis_node_sdk") / "chimera_contract.py"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def _source_commit() -> str:
    commit = _git("rev-parse", "HEAD")
    dirty = bool(_git("status", "--porcelain", "--", str(SOURCE)))
    return f"{commit}+dirty" if dirty else commit


def _remote_url() -> str:
    try:
        return _git("config", "--get", "remote.origin.url")
    except subprocess.CalledProcessError:
        return "local checkout (no remote configured)"


def _contract_version() -> int:
    # Import the canonical module directly rather than regexing the source,
    # so the stamped version can never drift from the real constant.
    sys.path.insert(0, str(REPO_ROOT))
    from protocols.chimera_contract import CONTRACT_VERSION  # noqa: E402

    return CONTRACT_VERSION


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def build_header(source_text: str) -> str:
    """Returns a comment block, not a docstring -- the source file already
    starts with its own module docstring immediately followed by `from
    __future__ import annotations`. Prepending a second triple-quoted
    string literal there is a real SyntaxError (Python's future-import
    placement rule rejects any statement, including a bare string literal,
    before it) -- confirmed by direct reproduction: `ast.parse()` does not
    catch this (it doesn't enforce future-import placement), but `compile()`
    and a real `import` both fail. Comments aren't statements, so they
    can't violate this rule regardless of what follows.
    """
    commit = _source_commit()
    version = _contract_version()
    remote = _remote_url()
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    content_hash = _content_hash(source_text)
    return (
        "# AUTO-GENERATED -- DO NOT EDIT.\n#\n"
        "# Vendored copy of Brain's canonical chimera wire contract. Brain\n"
        "# (protocols/chimera_contract.py) is the single source of truth (see\n"
        "# Brain/docs/DECISION_LOG.md ADR-013); JARVIS must not hand-edit this\n"
        "# file. To pick up upstream changes, re-run from the Brain repo:\n#\n"
        "#     python scripts/sync_chimera_contract.py --jarvis-root <path-to-JARVIS>\n#\n"
        f"# Source repo:      {remote}\n"
        f"# Source commit:    {commit}\n"
        f"# Contract version: {version}\n"
        f"# Generated (UTC):  {generated_at}\n"
        f"# Content hash:     {content_hash}  (sha256 of source, first 16 hex chars)\n"
    )


def _extract_stamped_hash(vendored_text: str) -> str | None:
    for line in vendored_text.splitlines():
        # Header lines are "# Content hash:     <hash>  (...)" -- strip a
        # leading comment marker before matching, so this stays agnostic to
        # whether the header is comment- or docstring-formatted.
        stripped = line.strip().lstrip("#").strip()
        if stripped.startswith("Content hash:"):
            return stripped.split(":", 1)[1].strip().split()[0]
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jarvis-root", required=True, type=Path)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the vendored copy is current; do not write.",
    )
    args = parser.parse_args()

    source_text = SOURCE.read_text(encoding="utf-8")
    target = args.jarvis_root / VENDORED_RELPATH

    if args.check:
        if not target.is_file():
            print(f"MISSING: {target} has never been generated.")
            return 1
        current = target.read_text(encoding="utf-8")
        current_hash = _extract_stamped_hash(current)
        if current_hash != _content_hash(source_text):
            print(f"STALE: {target} does not match current source.")
            return 1
        print("OK: vendored copy is current.")
        return 0

    header = build_header(source_text)
    # Only prepend, never rewrite the body -- keeps a vendored-vs-canonical
    # diff trivially reviewable (just diff after stripping the header).
    vendored_text = header + "\n" + source_text

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(vendored_text, encoding="utf-8")
    print(f"Wrote {target} (contract v{_contract_version()}, commit {_source_commit()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
