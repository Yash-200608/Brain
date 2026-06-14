"""SessionLogStore — append-only SQLite log per session."""
from __future__ import annotations

import sqlite3
import threading
import time
import uuid

from config import settings


class SessionLogStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or settings.sessions_db
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            # WAL: concurrent readers + single writer — matches the V2
            # per-session-actor write pattern.
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    started_at REAL,
                    user_input TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS turns (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    ts REAL,
                    user_input TEXT,
                    response TEXT,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
                """
            )

    def append(self, session_id: str, user_input: str, response: str) -> str:
        ts = time.time()
        turn_id = uuid.uuid4().hex
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sessions(id, started_at, user_input) VALUES (?,?,?)",
                (session_id, ts, user_input),
            )
            conn.execute(
                "INSERT INTO turns(id, session_id, ts, user_input, response) VALUES (?,?,?,?,?)",
                (turn_id, session_id, ts, user_input, response),
            )
        return turn_id

    def list_sessions(self, limit: int = 20) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, started_at, user_input FROM sessions ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_turns(self, session_id: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM turns WHERE session_id=? ORDER BY ts ASC",
                (session_id,),
            ).fetchall()
        return [dict(r) for r in rows]
