"""SessionService — episodic log access for orchestration and the API."""
from __future__ import annotations

from logs.store import SessionLogStore


class SessionService:
    def __init__(self, store: SessionLogStore | None = None) -> None:
        self.store = store or SessionLogStore()

    def append_turn(self, session_id: str, user_input: str, response: str) -> str:
        return self.store.append(session_id, user_input, response)

    def list_sessions(self, limit: int = 20) -> list[dict]:
        return self.store.list_sessions(limit=limit)

    def get_turns(self, session_id: str) -> list[dict]:
        return self.store.get_turns(session_id)
