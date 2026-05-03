"""GoalStore — SQLite-backed goal persistence."""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
import time
from typing import Iterable

from config import settings
from goals.models import Goal, GoalStatus, Subtask

logger = logging.getLogger(__name__)


class GoalStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or settings.goals_db
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS goals (
                    id TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    subtasks TEXT NOT NULL,
                    created_at REAL,
                    updated_at REAL
                )
                """
            )

    # -- writes --
    def upsert(self, goal: Goal) -> None:
        goal.updated_at = time.time()
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO goals(id, description, status, subtasks, created_at, updated_at)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                  description=excluded.description,
                  status=excluded.status,
                  subtasks=excluded.subtasks,
                  updated_at=excluded.updated_at
                """,
                (
                    goal.id,
                    goal.description,
                    goal.status.value,
                    json.dumps([s.__dict__ for s in goal.subtasks]),
                    goal.created_at,
                    goal.updated_at,
                ),
            )

    # -- reads --
    def list(self, status: GoalStatus | None = None) -> list[Goal]:
        q = "SELECT id, description, status, subtasks, created_at, updated_at FROM goals"
        args: tuple = ()
        if status:
            q += " WHERE status = ?"
            args = (status.value,)
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(q, args).fetchall()
        return [self._row_to_goal(r) for r in rows]

    def get(self, goal_id: str) -> Goal | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, description, status, subtasks, created_at, updated_at FROM goals WHERE id=?",
                (goal_id,),
            ).fetchone()
        return self._row_to_goal(row) if row else None

    # -- subtask completion --
    def complete_subtask(self, goal_id: str, subtask_text: str) -> bool:
        goal = self.get(goal_id)
        if not goal:
            return False
        for s in goal.subtasks:
            if s.text == subtask_text and not s.done:
                s.done = True
                s.completed_at = time.time()
        if all(s.done for s in goal.subtasks) and goal.subtasks:
            goal.status = GoalStatus.COMPLETE
        self.upsert(goal)
        return True

    _COMPLETE_RE = re.compile(
        r'COMPLETE_SUBTASK\s+goal_id="(?P<gid>[^"]+)"\s+subtask="(?P<sub>[^"]+)"',
        re.IGNORECASE,
    )

    def complete_subtask_from_instruction(self, instruction: str) -> bool:
        m = self._COMPLETE_RE.search(instruction or "")
        if not m:
            return False
        return self.complete_subtask(m.group("gid"), m.group("sub"))

    # -- helpers --
    @staticmethod
    def _row_to_goal(row: Iterable) -> Goal:
        gid, desc, status, subs_json, created, updated = row
        subs = [Subtask(**s) for s in json.loads(subs_json)]
        return Goal(
            id=gid,
            description=desc,
            status=GoalStatus(status),
            subtasks=subs,
            created_at=created,
            updated_at=updated,
        )
