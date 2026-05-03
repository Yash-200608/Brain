"""POST /api/query — main inference endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from api.schemas import QueryIn, QueryOut
from orchestrator.orchestrator import JarvisOrchestrator

router = APIRouter()
_orch = JarvisOrchestrator()


def get_orchestrator() -> JarvisOrchestrator:
    return _orch


@router.post("/query", response_model=QueryOut)
def query(payload: QueryIn, orch: JarvisOrchestrator = Depends(get_orchestrator)) -> QueryOut:
    if payload.session_id:
        orch.state.session_id = payload.session_id
    result = orch.handle(payload.query)
    return QueryOut(**result)
