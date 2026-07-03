import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "sync_chimera_contract.py"
VENDORED_RELPATH = Path("jarvis_node_sdk") / "chimera_contract.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )


def test_generates_vendored_copy_with_banner_and_version(tmp_path):
    result = _run("--jarvis-root", str(tmp_path))
    assert result.returncode == 0, result.stderr

    target = tmp_path / VENDORED_RELPATH
    assert target.is_file()

    text = target.read_text(encoding="utf-8")
    assert "AUTO-GENERATED -- DO NOT EDIT" in text
    assert "Contract version: 1" in text
    assert "Source commit:" in text
    assert "Content hash:" in text
    # Body is preserved verbatim after the generated header.
    assert "class ChimeraEnvelope(BaseModel):" in text


def test_check_passes_immediately_after_generation(tmp_path):
    gen = _run("--jarvis-root", str(tmp_path))
    assert gen.returncode == 0, gen.stderr

    check = _run("--jarvis-root", str(tmp_path), "--check")
    assert check.returncode == 0, check.stdout + check.stderr
    assert "OK" in check.stdout


def test_check_fails_when_vendored_copy_is_missing(tmp_path):
    check = _run("--jarvis-root", str(tmp_path), "--check")
    assert check.returncode != 0
    assert "MISSING" in check.stdout


def test_check_detects_staleness_when_stamped_hash_no_longer_matches_source(tmp_path):
    """--check compares the vendored file's *stamped* content hash against a
    fresh hash of the live source -- it does not re-hash the vendored body.
    Simulate drift by corrupting the stamped hash line directly (the same
    observable effect as the source having changed since generation,
    without mutating Brain's real source file mid-test)."""
    gen = _run("--jarvis-root", str(tmp_path))
    assert gen.returncode == 0, gen.stderr

    target = tmp_path / VENDORED_RELPATH
    text = target.read_text(encoding="utf-8")
    lines = [
        "# Content hash:     0000000000000000  (sha256 of source, first 16 hex chars)"
        if line.strip().lstrip("#").strip().startswith("Content hash:")
        else line
        for line in text.splitlines()
    ]
    target.write_text("\n".join(lines), encoding="utf-8")

    check = _run("--jarvis-root", str(tmp_path), "--check")
    assert check.returncode != 0
    assert "STALE" in check.stdout


def test_generated_vendored_copy_actually_imports_in_subprocess(tmp_path):
    """Regression guard for a real bug: Milestone 1's own verification only
    ran ast.parse() on the generated file, which does NOT catch a
    SyntaxError from two top-level docstrings before `from __future__
    import annotations` (ast.parse() doesn't enforce future-import
    placement; compile()/a real import both do). This actually imports the
    generated file in a fresh subprocess -- the same mechanism that will
    really consume it -- not a weaker syntactic check."""
    gen = _run("--jarvis-root", str(tmp_path))
    assert gen.returncode == 0, gen.stderr

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "from jarvis_node_sdk.chimera_contract import ChimeraEnvelope, RiskTier, sign, verify",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
