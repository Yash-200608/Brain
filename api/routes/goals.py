"""/api/goals routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import GoalIn, GoalOut
from goals.models import Goal, Subtask
from goals.store import GoalStore

router = APIRouter()
_store = GoalStore()


def _to_out(g: Goal) -> GoalOut:
    return GoalOut(
        id=g.id,
        description=g.description,
        status=g.status.value,
        subtasks=[s.__dict__ for s in g.subtasks],
    )


@router.get("/", response_model=list[GoalOut])
def list_goals() -> list[GoalOut]:
    return [_to_out(g) for g in _store.list()]


@router.post("/", response_model=GoalOut)
def create_goal(payload: GoalIn) -> GoalOut:
    goal = Goal(
        description=payload.description,
        subtasks=[Subtask(text=t) for t in payload.subtasks],
    )
    _store.upsert(goal)
    return _to_out(goal)


@router.get("/{goal_id}", response_model=GoalOut)
def get_goal(goal_id: str) -> GoalOut:
    g = _store.get(goal_id)
    if not g:
        raise HTTPException(404, "goal not found")
    return _to_out(g)
