"""/api/sessions routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from logs.store import SessionLogStore

router = APIRouter()
_store = SessionLogStore()


@router.get("/")
def list_sessions(limit: int = 20) -> list[dict]:
    return _store.list_sessions(limit=limit)


@router.get("/{session_id}/turns")
def get_turns(session_id: str) -> list[dict]:
    turns = _store.get_turns(session_id)
    if not turns:
        raise HTTPException(404, "session not found")
    return turns
