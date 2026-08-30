"""DispatchAudit -- the audit trail for every device-skill dispatch
(Priority #4 Milestone 7). Records who asked, what was classified, whether
an approval was involved, and what the node truthfully answered -- the
keystone demo's "every step is visible" requirement.

Append-only by convention: nothing in Brain updates or deletes audit rows.
Same devices.db file, its own table.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid

from config import settings


class DispatchAudit:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or settings.devices_db
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dispatch_audit (
                    id TEXT PRIMARY KEY,
                    ts REAL NOT NULL,
                    requester TEXT NOT NULL,
                    node TEXT NOT NULL,
                    skill TEXT NOT NULL,
                    params TEXT NOT NULL,
                    risk INTEGER NOT NULL,
                    approval_id TEXT,
                    outcome TEXT NOT NULL,
                    result TEXT
                )
                """
            )

    def record(
        self,
        *,
        requester: str,
        node: str,
        skill: str,
        params: dict,
        risk: int,
        outcome: str,
        approval_id: str | None = None,
        result: dict | None = None,
    ) -> str:
        row_id = uuid.uuid4().hex
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO dispatch_audit VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    row_id,
                    time.time(),
                    requester,
                    node,
                    skill,
                    json.dumps(params),
                    risk,
                    approval_id,
                    outcome,
                    json.dumps(result) if result is not None else None,
                ),
            )
        return row_id

    def list(self, limit: int = 50) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, ts, requester, node, skill, params, risk, approval_id, outcome, result "
                "FROM dispatch_audit ORDER BY ts DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "id": r[0],
                "ts": r[1],
                "requester": r[2],
                "node": r[3],
                "skill": r[4],
                "params": json.loads(r[5]),
                "risk": r[6],
                "approval_id": r[7],
                "outcome": r[8],
                "result": json.loads(r[9]) if r[9] is not None else None,
            }
            for r in rows
        ]

    def trial_stats(self, since_ts: float | None = None) -> dict:
        """Aggregate counters for M11 trial instrumentation."""
        clause = ""
        params: tuple = ()
        if since_ts is not None:
            clause = " WHERE ts >= ?"
            params = (since_ts,)

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                f"SELECT ts, skill, outcome FROM dispatch_audit{clause} ORDER BY ts",
                params,
            ).fetchall()

        from trial.confirmed_classes import normalize_skill

        by_outcome: dict[str, int] = {}
        by_skill: dict[str, int] = {}
        success_by_class: dict[str, int] = {}
        any_by_class: dict[str, int] = {}
        first_ts: float | None = None
        last_ts: float | None = None

        for ts, skill, outcome in rows:
            first_ts = ts if first_ts is None else min(first_ts, ts)
            last_ts = ts if last_ts is None else max(last_ts, ts)
            by_outcome[outcome] = by_outcome.get(outcome, 0) + 1
            by_skill[skill] = by_skill.get(skill, 0) + 1
            cls = normalize_skill(skill)
            any_by_class[cls] = any_by_class.get(cls, 0) + 1
            if outcome == "responded":
                success_by_class[cls] = success_by_class.get(cls, 0) + 1

        return {
            "total": len(rows),
            "first_ts": first_ts,
            "last_ts": last_ts,
            "by_outcome": by_outcome,
            "by_skill": by_skill,
            "success_by_class": success_by_class,
            "any_by_class": any_by_class,
        }
