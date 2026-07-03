"""DeviceStore -- SQLite-backed device (known node) persistence."""
from __future__ import annotations

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

    # -- writes --
    def upsert(self, device: Device) -> None:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO devices(node, first_seen, last_seen)
                VALUES (?,?,?)
                ON CONFLICT(node) DO UPDATE SET
                  last_seen=excluded.last_seen
                """,
                (device.node, device.first_seen, device.last_seen),
            )

    def mark_seen(self, node: str) -> Device:
        """Get-or-create `node`, bump its `last_seen` to now, persist, and
        return the updated Device."""
        device = self.get(node) or Device(node=node)
        device.last_seen = time.time()
        self.upsert(device)
        return device

    # -- reads --
    def list(self) -> list[Device]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT node, first_seen, last_seen FROM devices"
            ).fetchall()
        return [self._row_to_device(r) for r in rows]

    def get(self, node: str) -> Device | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT node, first_seen, last_seen FROM devices WHERE node=?",
                (node,),
            ).fetchone()
        return self._row_to_device(row) if row else None

    # -- helpers --
    @staticmethod
    def _row_to_device(row: Iterable) -> Device:
        node, first_seen, last_seen = row
        return Device(node=node, first_seen=first_seen, last_seen=last_seen)
