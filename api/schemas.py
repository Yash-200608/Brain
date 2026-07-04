"""Pydantic request / response schemas."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QueryIn(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    session_id: str | None = None


class QueryOut(BaseModel):
    session_id: str
    response: str
    memory_used: list[str] = []
    tasks: list[dict] = []


class GoalIn(BaseModel):
    description: str
    subtasks: list[str] = []


class GoalOut(BaseModel):
    id: str
    description: str
    status: str
    subtasks: list[dict]


class MemoryWriteIn(BaseModel):
    text: str
    importance: float = 0.5
    metadata: dict[str, Any] = {}


class MemorySearchIn(BaseModel):
    query: str
    top_k: int = 8


class HealthOut(BaseModel):
    status: str
    components: dict[str, str]


class DeviceOut(BaseModel):
    node: str
    first_seen: float
    last_seen: float
    state: dict | None = None
    last_state_at: float | None = None
    is_online: bool
