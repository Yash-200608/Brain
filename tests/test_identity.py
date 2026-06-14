from identity import (
    SCOPE_ADMIN,
    SCOPE_MEMORY_WRITE,
    IdentityService,
    Principal,
    default_scopes,
    owner_principal,
)


def test_owner_principal_has_all_scopes():
    p = owner_principal()
    assert p.user_id == "owner"
    assert p.client_id == "local"
    assert p.has_scope(SCOPE_ADMIN)
    assert p.has_scope(SCOPE_MEMORY_WRITE)


def test_default_scopes_exclude_admin():
    p = Principal(user_id="alice", scopes=default_scopes())
    assert not p.has_scope(SCOPE_ADMIN)
    assert p.has_scope(SCOPE_MEMORY_WRITE)


def test_admin_scope_implies_everything():
    p = Principal(user_id="root", scopes=frozenset({SCOPE_ADMIN}))
    assert p.has_scope("anything.at.all")


def test_resolve_known_and_unknown_keys():
    svc = IdentityService(api_keys={"tok-alice": "alice"})
    resolved = svc.resolve("tok-alice")
    assert resolved is not None
    assert resolved.user_id == "alice"
    assert resolved.client_id == "api"
    assert svc.resolve("unknown") is None
    assert svc.resolve("") is None
    assert svc.resolve(None) is None


def test_default_principal_is_owner():
    svc = IdentityService(api_keys={})
    assert svc.default_principal().user_id == "owner"


def test_register_and_revoke_key():
    svc = IdentityService(api_keys={})
    svc.register_key("tok-bob", Principal(user_id="bob", client_id="mobile"))
    resolved = svc.resolve("tok-bob")
    assert resolved is not None
    assert resolved.client_id == "mobile"
    assert svc.revoke_key("tok-bob")
    assert svc.resolve("tok-bob") is None
    assert not svc.revoke_key("tok-bob")
