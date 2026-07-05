"""IdentityService — resolves credentials to Principals.

Foundation behavior (deliberate):
  * No request is ever rejected here; unknown or absent credentials fall back
    to the owner principal at the call site. Enforcement is a future phase.
  * Keys are held in memory, seeded from ``settings.api_keys``
    (``token -> user_id``). Richer key records (per-key scopes, client ids)
    layer on via :meth:`register_key` without changing this interface.
"""
from __future__ import annotations

import hashlib
import threading

from config import settings
from identity.models import Principal, default_scopes, owner_principal

class IdentityService:
    def __init__(
        self,
        api_keys: dict[str, str] | None = None,
        *,
        default_user_id: str | None = None,
    ) -> None:
        self._default_user_id = default_user_id or settings.default_user_id
        self._lock = threading.RLock()
        self._keys: dict[str, Principal] = {}
        seed = api_keys if api_keys is not None else settings.api_keys
        for token, user_id in seed.items():
            if token:
                # metadata.key_id is a token digest, never the token itself
                # (it flows into audit-trail rows). It is what makes two
                # keys with the same user_id distinguishable for the
                # approval flow's distinct-principal check (NP-7).
                key_id = hashlib.sha256(token.encode()).hexdigest()[:12]
                self._keys[token] = Principal(
                    user_id=user_id,
                    client_id="api",
                    scopes=default_scopes(),
                    metadata={"key_id": key_id},
                )

    def default_principal(self) -> Principal:
        """The principal used when no credential is presented (single-user mode)."""
        return owner_principal(self._default_user_id)

    def resolve(self, token: str | None) -> Principal | None:
        """Resolve a bearer token. Returns None when unknown — never raises."""
        token = (token or "").strip()
        if not token:
            return None
        with self._lock:
            return self._keys.get(token)

    def register_key(self, token: str, principal: Principal) -> None:
        if not token:
            raise ValueError("token must be non-empty")
        with self._lock:
            self._keys[token] = principal

    def revoke_key(self, token: str) -> bool:
        with self._lock:
            return self._keys.pop(token, None) is not None


_service: IdentityService | None = None
_service_lock = threading.Lock()


def get_identity_service() -> IdentityService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = IdentityService()
    return _service


def set_identity_service(service: IdentityService | None) -> None:
    """Replace the default service (primarily for tests)."""
    global _service
    with _service_lock:
        _service = service
