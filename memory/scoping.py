"""Memory scoping — the multi-user metadata foundation.

Every memory written through the service layer carries scope metadata so the
store is multi-user-ready *before* multi-user enforcement exists. Existing
data is NOT migrated; absence of ``user_id`` means "legacy single-user item"
and is treated as owned by the default user when filtering arrives.

Scope fields:
  user_id     — owner principal of the memory
  visibility  — private | shared | global
  session_id  — provenance session (optional)
  origin      — which component wrote it (reflection, api, memory_agent, ...)
  trust_level — how much downstream reasoning should trust it
"""
from __future__ import annotations

from typing import Any

VISIBILITY_PRIVATE = "private"
VISIBILITY_SHARED = "shared"
VISIBILITY_GLOBAL = "global"
VISIBILITIES = (VISIBILITY_PRIVATE, VISIBILITY_SHARED, VISIBILITY_GLOBAL)

TRUST_HIGH = "high"
TRUST_STANDARD = "standard"
TRUST_LOW = "low"
TRUST_LEVELS = (TRUST_HIGH, TRUST_STANDARD, TRUST_LOW)

SCOPE_FIELDS = ("user_id", "visibility", "session_id", "origin", "trust_level")


def apply_scope(
    metadata: dict[str, Any] | None,
    *,
    user_id: str,
    visibility: str = VISIBILITY_PRIVATE,
    session_id: str | None = None,
    origin: str | None = None,
    trust_level: str = TRUST_STANDARD,
) -> dict[str, Any]:
    """Merge scope fields into ``metadata`` without clobbering explicit values."""
    meta = dict(metadata or {})
    meta.setdefault("user_id", user_id)
    meta.setdefault("visibility", visibility)
    if session_id is not None:
        meta.setdefault("session_id", session_id)
    if origin is not None:
        meta.setdefault("origin", origin)
    meta.setdefault("trust_level", trust_level)
    return meta
