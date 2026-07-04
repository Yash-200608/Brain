"""/api/memory routes — served through the MemoryService layer."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from agents.memory_agent import MemoryAgent
from api.deps import require_scope
from api.schemas import MemorySearchIn, MemoryWriteIn
from events import get_event_bus
from identity import SCOPE_MEMORY_READ, SCOPE_MEMORY_WRITE
from services import MemoryService

router = APIRouter()
_service = MemoryService(MemoryAgent(), bus=get_event_bus())


@router.post("/search", dependencies=[Depends(require_scope(SCOPE_MEMORY_READ))])
def search(payload: MemorySearchIn, request: Request) -> list[dict]:
    principal = getattr(request.state, "principal", None)
    return _service.search(payload.query, top_k=payload.top_k, principal=principal)


@router.post("/write", dependencies=[Depends(require_scope(SCOPE_MEMORY_WRITE))])
def write(payload: MemoryWriteIn, request: Request) -> dict:
    principal = getattr(request.state, "principal", None)
    mid = _service.write(
        payload.text,
        importance=payload.importance,
        metadata=payload.metadata,
        principal=principal,
        origin="api",
    )
    return {"id": mid}
