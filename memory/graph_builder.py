"""GraphBuilder — extract entity relationships into a simple graph store.

Optional layer (V4+). Stores edges as (subject, relation, object) triples.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)


class GraphBuilder:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or str(Path(settings.chroma_path).parent / "graph.db")
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    object TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    created_at REAL DEFAULT (strftime('%s','now')),
                    UNIQUE(subject, relation, object)
                )
                """
            )

    def add_edge(self, subject: str, relation: str, obj: str, weight: float = 1.0) -> None:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO edges(subject, relation, object, weight) VALUES (?,?,?,?)
                ON CONFLICT(subject, relation, object) DO UPDATE SET weight=weight + excluded.weight
                """,
                (subject, relation, obj, weight),
            )

    def neighbors(self, node: str, limit: int = 25) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT subject, relation, object, weight FROM edges
                WHERE subject=? OR object=? ORDER BY weight DESC LIMIT ?
                """,
                (node, node, limit),
            ).fetchall()
        return [{"subject": r[0], "relation": r[1], "object": r[2], "weight": r[3]} for r in rows]

    def to_json(self) -> str:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT subject, relation, object, weight FROM edges").fetchall()
        return json.dumps([{"s": r[0], "r": r[1], "o": r[2], "w": r[3]} for r in rows])
