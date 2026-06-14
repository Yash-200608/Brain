"""POST /api/query — main inference endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from api.schemas import QueryIn, QueryOut
from orchestrator.orchestrator import JarvisOrchestrator

router = APIRouter()
_orch = JarvisOrchestrator()


def get_orchestrator() -> JarvisOrchestrator:
    return _orch


@router.post("/query", response_model=QueryOut)
def query(
    payload: QueryIn,
    request: Request,
    orch: JarvisOrchestrator = Depends(get_orchestrator),
) -> QueryOut:
    # Principal resolved by AuthMiddleware (owner by default — non-enforcing).
    principal = getattr(request.state, "principal", None)
    result = orch.handle(payload.query, session_id=payload.session_id, principal=principal)
    return QueryOut(**result)
