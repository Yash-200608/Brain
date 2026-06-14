"""Brain V2 identity foundations — Principal, scopes, IdentityService."""
from .models import (
    ALL_SCOPES,
    SCOPE_ADMIN,
    SCOPE_GOALS,
    SCOPE_MEMORY_READ,
    SCOPE_MEMORY_WRITE,
    SCOPE_QUERY,
    SCOPE_SESSIONS,
    Principal,
    default_scopes,
    owner_principal,
)
from .service import IdentityService, get_identity_service, set_identity_service

__all__ = [
    "ALL_SCOPES",
    "SCOPE_ADMIN",
    "SCOPE_GOALS",
    "SCOPE_MEMORY_READ",
    "SCOPE_MEMORY_WRITE",
    "SCOPE_QUERY",
    "SCOPE_SESSIONS",
    "Principal",
    "default_scopes",
    "owner_principal",
    "IdentityService",
    "get_identity_service",
    "set_identity_service",
]
