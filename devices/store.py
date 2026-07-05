"""DeviceStore -- SQLite-backed device (known node) persistence."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Iterable

from config import settings
from devices.models import Device


class DeviceStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or settings.devices_db
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    node TEXT PRIMARY KEY,
                    first_seen REAL,
                    last_seen REAL
                )
                """
            )
            # CREATE TABLE IF NOT EXISTS is a no-op against a database that
            # already has an older table on disk -- add new columns
            # idempotently so existing devices.db files (and every
            # subsequent process start) migrate safely.
            existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(devices)")}
            if "state" not in existing_cols:
                conn.execute("ALTER TABLE devices ADD COLUMN state TEXT")
            if "last_state_at" not in existing_cols:
                conn.execute("ALTER TABLE devices ADD COLUMN last_state_at REAL")
            if "skills" not in existing_cols:
                conn.execute("ALTER TABLE devices ADD COLUMN skills TEXT")
            if "skills_declared_at" not in existing_cols:
                conn.execute("ALTER TABLE devices ADD COLUMN skills_declared_at REAL")

    # -- writes --
    def upsert(self, device: Device) -> None:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO devices(node, first_seen, last_seen, state, last_state_at, skills, skills_declared_at)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(node) DO UPDATE SET
                  last_seen=excluded.last_seen,
                  state=excluded.state,
                  last_state_at=excluded.last_state_at,
                  skills=excluded.skills,
                  skills_declared_at=excluded.skills_declared_at
                """,
                (
                    device.node,
                    device.first_seen,
                    device.last_seen,
                    json.dumps(device.state) if device.state is not None else None,
                    device.last_state_at,
                    json.dumps(device.skills) if device.skills is not None else None,
                    device.skills_declared_at,
                ),
            )

    def mark_seen(self, node: str) -> Device:
        """Get-or-create `node`, bump its `last_seen` to now, persist, and
        return the updated Device. Reuses the fetched Device's existing
        state/last_state_at/skills rather than a blank one, so a
        presence-only call never clobbers previously-recorded data."""
        device = self.get(node) or Device(node=node)
        device.last_seen = time.time()
        self.upsert(device)
        return device

    def record_state(self, node: str, state: dict) -> Device:
        """Get-or-create `node`, record `state`, bump `last_seen` (a state
        report is itself proof of liveness), persist, and return the
        updated Device."""
        device = self.get(node) or Device(node=node)
        now = time.time()
        device.last_seen = now
        device.state = state
        device.last_state_at = now
        self.upsert(device)
        return device

    def record_capabilities(self, node: str, skills: list[str]) -> Device:
        """Get-or-create `node`, record its declared `skills`, bump
        `last_seen` (a declaration is itself proof of liveness, same
        reasoning as record_state), persist, and return the updated
        Device. Overwrites any previously-declared skill list wholesale --
        a node's capability declaration is a complete snapshot each time,
        not an incremental diff (mirrors how state reports are opaque
        whole-snapshot blobs, not patches)."""
        device = self.get(node) or Device(node=node)
        now = time.time()
        device.last_seen = now
        device.skills = skills
        device.skills_declared_at = now
        self.upsert(device)
        return device

    # -- reads --
    def list(self) -> list[Device]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT node, first_seen, last_seen, state, last_state_at, skills, skills_declared_at FROM devices"
            ).fetchall()
        return [self._row_to_device(r) for r in rows]

    def get(self, node: str) -> Device | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT node, first_seen, last_seen, state, last_state_at, skills, skills_declared_at FROM devices WHERE node=?",
                (node,),
            ).fetchone()
        return self._row_to_device(row) if row else None

    # -- helpers --
    @staticmethod
    def _row_to_device(row: Iterable) -> Device:
        node, first_seen, last_seen, state, last_state_at, skills, skills_declared_at = row
        return Device(
            node=node,
            first_seen=first_seen,
            last_seen=last_seen,
            state=json.loads(state) if state is not None else None,
            last_state_at=last_state_at,
            skills=json.loads(skills) if skills is not None else None,
            skills_declared_at=skills_declared_at,
        )
