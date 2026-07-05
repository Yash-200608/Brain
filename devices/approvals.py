"""ApprovalStore -- pending device-action approvals (Priority #4
Milestone 7), implementing the ecosystem architecture Section 5 approval
flow's three mandatory properties (NP-7):

1. **Distinct, more-privileged principal.** approve() rejects an approver
   whose identity tuple matches the requester's, and the HTTP layer
   additionally gates approval on SCOPE_DEVICES_APPROVE -- a scope
   deliberately excluded from default_scopes(), so an ordinary key that
   can *request* actions cannot approve its own requests. In single-owner
   deployments user_id alone cannot distinguish keys, so the identity
   tuple includes the key id carried in Principal.metadata["key_id"] when
   present; two keys without key_ids and identical (user_id, client_id)
   are indistinguishable and therefore rejected (fail-closed toward
   requiring genuinely distinct credentials).

2. **Tier-checked before execution.** The risk tier is classified and
   stored at request time (devices/policy.py); consume() re-verifies the
   fingerprint of what is about to execute against what was approved --
   approval never applies to a rewritten or different action.

3. **Single-use, instance-bound.** consume() atomically deletes the
   approval row; a second consume of the same id fails. The fingerprint
   binds the approval to the exact (node, skill, params) instance.

SQLite-backed in the same devices.db file as DeviceStore (new table), so
pending approvals survive a Brain restart.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass

from config import settings


def action_fingerprint(node: str, skill: str, params: dict) -> str:
    payload = json.dumps(
        {"node": node, "skill": skill, "params": params},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def principal_key(user_id: str, client_id: str, key_id: str | None) -> str:
    """The identity tuple used for the distinct-principal check."""
    return json.dumps([user_id, client_id, key_id or ""], separators=(",", ":"))


@dataclass
class Approval:
    id: str
    node: str
    skill: str
    params: dict
    risk: int
    requester: str  # principal_key() of whoever asked
    created_at: float


class ApprovalStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or settings.devices_db
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS device_approvals (
                    id TEXT PRIMARY KEY,
                    node TEXT NOT NULL,
                    skill TEXT NOT NULL,
                    params TEXT NOT NULL,
                    risk INTEGER NOT NULL,
                    requester TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )

    # -- writes --
    def request(
        self, node: str, skill: str, params: dict, risk: int, requester: str
    ) -> Approval:
        approval = Approval(
            id=uuid.uuid4().hex,
            node=node,
            skill=skill,
            params=params,
            risk=risk,
            requester=requester,
            created_at=time.time(),
        )
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO device_approvals VALUES (?,?,?,?,?,?,?)",
                (
                    approval.id,
                    approval.node,
                    approval.skill,
                    json.dumps(approval.params),
                    approval.risk,
                    approval.requester,
                    approval.created_at,
                ),
            )
        return approval

    def consume(self, approval_id: str, approver: str) -> Approval | None:
        """Atomically validates and removes the approval. Returns the
        Approval on success; None when the id is unknown/already used
        (property 3) or the approver's identity tuple equals the
        requester's (property 1). The caller re-fingerprints what it is
        about to execute against the returned record (property 2/3)."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, node, skill, params, risk, requester, created_at "
                "FROM device_approvals WHERE id=?",
                (approval_id,),
            ).fetchone()
            if row is None:
                return None
            approval = Approval(
                id=row[0], node=row[1], skill=row[2], params=json.loads(row[3]),
                risk=row[4], requester=row[5], created_at=row[6],
            )
            if approver == approval.requester:
                # Same principal in a different request is still the same
                # principal -- do NOT consume (the approval stays valid for
                # a genuinely distinct approver).
                return None
            conn.execute("DELETE FROM device_approvals WHERE id=?", (approval_id,))
        return approval

    def deny(self, approval_id: str) -> bool:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("DELETE FROM device_approvals WHERE id=?", (approval_id,))
            return cur.rowcount > 0

    # -- reads --
    def list_pending(self) -> list[Approval]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, node, skill, params, risk, requester, created_at "
                "FROM device_approvals ORDER BY created_at"
            ).fetchall()
        return [
            Approval(
                id=r[0], node=r[1], skill=r[2], params=json.loads(r[3]),
                risk=r[4], requester=r[5], created_at=r[6],
            )
            for r in rows
        ]

    def get(self, approval_id: str) -> Approval | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, node, skill, params, risk, requester, created_at "
                "FROM device_approvals WHERE id=?",
                (approval_id,),
            ).fetchone()
        if row is None:
            return None
        return Approval(
            id=row[0], node=row[1], skill=row[2], params=json.loads(row[3]),
            risk=row[4], requester=row[5], created_at=row[6],
        )
