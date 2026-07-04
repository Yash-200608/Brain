"""/api/goals routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.deps import require_scope
from api.schemas import GoalIn, GoalOut
from goals.models import Goal, Subtask
from goals.store import GoalStore
from identity import SCOPE_GOALS

router = APIRouter()
_store = GoalStore()


def _to_out(g: Goal) -> GoalOut:
    return GoalOut(
        id=g.id,
        description=g.description,
        status=g.status.value,
        subtasks=[s.__dict__ for s in g.subtasks],
    )


@router.get(
    "/",
    response_model=list[GoalOut],
    dependencies=[Depends(require_scope(SCOPE_GOALS))],
)
def list_goals() -> list[GoalOut]:
    return [_to_out(g) for g in _store.list()]


@router.post(
    "/",
    response_model=GoalOut,
    dependencies=[Depends(require_scope(SCOPE_GOALS))],
)
def create_goal(payload: GoalIn) -> GoalOut:
    goal = Goal(
        description=payload.description,
        subtasks=[Subtask(text=t) for t in payload.subtasks],
    )
    _store.upsert(goal)
    return _to_out(goal)


@router.get(
    "/{goal_id}",
    response_model=GoalOut,
    dependencies=[Depends(require_scope(SCOPE_GOALS))],
)
def get_goal(goal_id: str) -> GoalOut:
    g = _store.get(goal_id)
    if not g:
        raise HTTPException(404, "goal not found")
    return _to_out(g)
