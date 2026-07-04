"""Identity models — who is talking to the Brain.

Brain is the authoritative identity holder. Jarvis, Chimera and mobile nodes
are clients: each presents a credential that resolves to a
:class:`Principal`. In V2-foundation, authentication is NOT enforced — every
request resolves to a principal (the owner by default) so single-user
operation is unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# -- scopes ------------------------------------------------------------------
SCOPE_QUERY = "query"
SCOPE_MEMORY_READ = "memory.read"
SCOPE_MEMORY_WRITE = "memory.write"
SCOPE_GOALS = "goals"
SCOPE_SESSIONS = "sessions"
# Devices split read from action deliberately (Priority #4 M1): reading the
# registry is low-privilege; invoking a device-level action (ping today,
# skill dispatch + approval in later P4 milestones) is the consequential
# operation PRIORITY-2-READINESS-REVIEW.md named as the scope-enforcement
# trigger. Keeping them separate lets a future narrow key read device state
# without being able to command devices.
SCOPE_DEVICES_READ = "devices.read"
SCOPE_DEVICES_ACTION = "devices.action"
SCOPE_ADMIN = "admin"

ALL_SCOPES: frozenset[str] = frozenset(
    {
        SCOPE_QUERY,
        SCOPE_MEMORY_READ,
        SCOPE_MEMORY_WRITE,
        SCOPE_GOALS,
        SCOPE_SESSIONS,
        SCOPE_DEVICES_READ,
        SCOPE_DEVICES_ACTION,
        SCOPE_ADMIN,
    }
)


def default_scopes() -> frozenset[str]:
    """Scopes granted to an ordinary authenticated client (everything but admin)."""
    return frozenset(ALL_SCOPES - {SCOPE_ADMIN})


# -- principal ---------------------------------------------------------------
@dataclass(frozen=True)
class Principal:
    """The resolved identity of a caller.

    ``user_id``   — the human (or system) the request acts on behalf of.
    ``client_id`` — which client surface made the call (jarvis, chimera,
                    a mobile node id, "local" for the CLI, "api" generically).
    ``scopes``    — capability set; ``admin`` implies everything.
    ``metadata``  — free-form extras (device info, key id, ...).
    """

    user_id: str
    client_id: str = "local"
    scopes: frozenset[str] = field(default_factory=default_scopes)
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_scope(self, scope: str) -> bool:
        return SCOPE_ADMIN in self.scopes or scope in self.scopes


def owner_principal(user_id: str | None = None) -> Principal:
    """The implicit single-user principal: full access, local client."""
    from config import settings

    return Principal(
        user_id=user_id or settings.default_user_id,
        client_id="local",
        scopes=ALL_SCOPES,
    )
