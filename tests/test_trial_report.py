"""Tests for Priority #4 M11 trial instrumentation."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from devices.audit import DispatchAudit
from trial.legacy_reader import read_legacy_invocations
from trial.report import build_trial_report, format_markdown


@pytest.fixture()
def audit_db(tmp_path: Path) -> DispatchAudit:
    return DispatchAudit(db_path=str(tmp_path / "devices.db"))


def test_trial_stats_empty(audit_db: DispatchAudit) -> None:
    stats = audit_db.trial_stats()
    assert stats["total"] == 0
    assert stats["by_outcome"] == {}


def test_trial_report_spine_coverage(audit_db: DispatchAudit) -> None:
    audit_db.record(
        requester="u1", node="pc", skill="phone.battery", params={},
        risk=0, outcome="responded", result={"ok": True},
    )
    audit_db.record(
        requester="u1", node="pc", skill="pc.shell.run", params={"command": "echo"},
        risk=2, outcome="approval_requested", approval_id="a1",
    )
    report = build_trial_report(audit_db, legacy_log_path=None)
    assert report["spine"]["total_events"] == 2
    assert report["confirmed_classes"]["phone.battery"]["spine_success"] == 1
    assert report["criteria"]["command_coverage"] is False  # only one class


def test_trial_report_legacy_adoption(tmp_path: Path, audit_db: DispatchAudit) -> None:
    log = tmp_path / "legacy.jsonl"
    log.write_text(
        json.dumps({"ts": time.time(), "command_class": "phone.battery", "target": "phone", "action": "get_battery"})
        + "\n",
        encoding="utf-8",
    )
    report = build_trial_report(audit_db, legacy_log_path=str(log))
    assert report["legacy"]["total_invocations"] == 1
    assert report["criteria"]["legacy_zero_for_covered"] is False


def test_trial_report_since_ts(audit_db: DispatchAudit) -> None:
    old = time.time() - 3600
    new = time.time()
    audit_db.record(
        requester="u1", node="n", skill="phone.battery", params={},
        risk=0, outcome="responded", result={},
    )
    # Manually skew ts by re-recording with filter — use since between
    report = build_trial_report(audit_db, since_ts=new - 1)
    assert report["spine"]["total_events"] >= 1


def test_format_markdown(audit_db: DispatchAudit) -> None:
    md = format_markdown(build_trial_report(audit_db))
    assert "# Priority #4 Trial Report" in md
    assert "phone.battery" in md


def test_read_legacy_missing_path() -> None:
    assert read_legacy_invocations("/nonexistent/path.jsonl") == []


def test_trial_report_route(monkeypatch, tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from api.routes import devices as devices_route
    from api.server import app
    from identity import IdentityService, set_identity_service

    audit = DispatchAudit(db_path=str(tmp_path / "d.db"))
    monkeypatch.setattr(devices_route, "_audit", audit)
    set_identity_service(IdentityService(api_keys={"tok": "owner"}))
    client = TestClient(app)
    r = client.get("/api/devices/trial-report", headers={"Authorization": "Bearer tok"})
    set_identity_service(None)
    assert r.status_code == 200
    body = r.json()
    assert "criteria" in body
    assert "confirmed_classes" in body
