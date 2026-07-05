"""Route-level approval-flow tests (Priority #4 Milestone 7) -- NP-7's
three properties enforced through the real FastAPI app + AuthMiddleware +
scope layer, with the broker faked via set_mqtt_client.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from api.routes import devices as devices_route
from api.server import app
from config import settings
from devices.approvals import ApprovalStore, principal_key
from devices.audit import DispatchAudit
from devices.dispatcher import DeviceDispatcher
from devices.store import DeviceStore
from identity import (
    SCOPE_DEVICES_APPROVE,
    SCOPE_DEVICES_READ,
    IdentityService,
    Principal,
    set_identity_service,
)
from mqtt import set_mqtt_client
from mqtt.client import BrainMqttClient
from protocols.chimera_contract import ChimeraEnvelope, sign

KEY = "f" * 64
NODE = "jarvis-core-pc"

REQUESTER_TUPLE = ("owner", "api", "key-req")


def teardown_function() -> None:
    set_identity_service(None)
    set_mqtt_client(None)


def _wire(monkeypatch, tmp_path, *, declared: list[str]):
    """Fresh per-test stores swapped into the route module, plus an
    identity service with a requester key, an approver key, and a
    default-scoped key."""
    db = str(tmp_path / "d.db")
    store = DeviceStore(db_path=db)
    store.record_capabilities(NODE, declared)
    approvals = ApprovalStore(db_path=db)
    audit = DispatchAudit(db_path=db)
    dispatcher = DeviceDispatcher(store=store, audit=audit)
    monkeypatch.setattr(devices_route, "_store", store)
    monkeypatch.setattr(devices_route, "_approvals", approvals)
    monkeypatch.setattr(devices_route, "_audit", audit)
    monkeypatch.setattr(devices_route, "_dispatcher", dispatcher)
    monkeypatch.setattr(settings, "mqtt_enabled", True)
    monkeypatch.setattr(settings, "mqtt_hmac_key", KEY)

    svc = IdentityService(api_keys={})
    svc.register_key(
        "tok-requester",
        Principal(
            user_id="owner", client_id="api",
            scopes=frozenset({SCOPE_DEVICES_READ}),
            metadata={"key_id": "key-req"},
        ),
    )
    svc.register_key(
        "tok-approver",
        Principal(
            user_id="owner", client_id="api",
            scopes=frozenset({SCOPE_DEVICES_APPROVE, SCOPE_DEVICES_READ}),
            metadata={"key_id": "key-app"},
        ),
    )
    svc.register_key(
        "tok-requester-approver-scope",
        Principal(
            user_id="owner", client_id="api",
            scopes=frozenset({SCOPE_DEVICES_APPROVE}),
            metadata={"key_id": "key-req"},  # same identity tuple as requester
        ),
    )
    set_identity_service(svc)
    return approvals, audit


def _pending(approvals: ApprovalStore, params: dict | None = None):
    return approvals.request(
        NODE, "pc.shell.run", params or {"command": "whoami"}, 2,
        principal_key(*REQUESTER_TUPLE),
    )


def _fake_responder_client(action: str, params: dict) -> BrainMqttClient:
    client = BrainMqttClient(host="localhost", port=1883, client_id="test")

    class _Msg:
        def __init__(self, topic, payload):
            self.topic, self.payload = topic, payload

    class _Msgs:
        def __init__(self, msgs):
            self._msgs = msgs

        def __aiter__(self):
            return self._gen()

        async def _gen(self):
            for m in self._msgs:
                yield m

    class _Fake:
        def __init__(self, messages):
            self.messages = messages

    async def fake_publish(topic, payload, *, qos=None, retain=False):
        if not topic.endswith("/cmd"):
            return
        response = ChimeraEnvelope(
            node=NODE, verb="response", action=action, params=params,
            request_id=payload.get("request_id"),
        )
        data = json.dumps(sign(response, KEY).model_dump(), separators=(",", ":")).encode()
        await client._dispatch_loop(_Fake(_Msgs([_Msg(f"chimera/{NODE}/response", data)])))

    client.publish = fake_publish  # type: ignore[method-assign]
    return client


def test_approve_requires_the_approve_scope(monkeypatch, tmp_path) -> None:
    """Privileged-above: a key with read (default-tier) scope cannot
    approve -- devices.approve is not in default_scopes."""
    approvals, _ = _wire(monkeypatch, tmp_path, declared=["pc.shell.run"])
    a = _pending(approvals)
    client = TestClient(app)

    r = client.post(
        f"/api/devices/approvals/{a.id}/approve",
        headers={"Authorization": "Bearer tok-requester"},
    )

    assert r.status_code == 403


def test_same_identity_tuple_cannot_approve_own_request(monkeypatch, tmp_path) -> None:
    """Distinct-principal: a key that RESOLVES to the requester's identity
    tuple is rejected even when it holds the approve scope -- 'never the
    same caller in a different field of the same request', nor in a
    different request."""
    approvals, _ = _wire(monkeypatch, tmp_path, declared=["pc.shell.run"])
    a = _pending(approvals)
    client = TestClient(app)

    r = client.post(
        f"/api/devices/approvals/{a.id}/approve",
        headers={"Authorization": "Bearer tok-requester-approver-scope"},
    )

    assert r.status_code == 403
    assert "distinct" in r.json()["detail"]
    # and the approval is NOT burned:
    assert approvals.get(a.id) is not None


def test_distinct_approver_dispatches_the_stored_action(monkeypatch, tmp_path) -> None:
    approvals, audit = _wire(monkeypatch, tmp_path, declared=["pc.shell.run"])
    a = _pending(approvals, params={"command": "echo approved"})
    set_mqtt_client(_fake_responder_client("pc.shell.run", {"ok": True, "stdout": "done"}))
    client = TestClient(app)

    r = client.post(
        f"/api/devices/approvals/{a.id}/approve",
        headers={"Authorization": "Bearer tok-approver"},
    )

    assert r.status_code == 200
    body = r.json()
    assert body["skill"] == "pc.shell.run"
    assert body["result"] == {"ok": True, "stdout": "done"}
    row = audit.list()[0]
    assert row["approval_id"] == a.id
    assert row["params"] == {"command": "echo approved"}  # the STORED instance


def test_replaying_a_consumed_approval_is_404(monkeypatch, tmp_path) -> None:
    approvals, _ = _wire(monkeypatch, tmp_path, declared=["pc.shell.run"])
    a = _pending(approvals)
    set_mqtt_client(_fake_responder_client("pc.shell.run", {"ok": True}))
    client = TestClient(app)
    headers = {"Authorization": "Bearer tok-approver"}

    first = client.post(f"/api/devices/approvals/{a.id}/approve", headers=headers)
    replay = client.post(f"/api/devices/approvals/{a.id}/approve", headers=headers)

    assert first.status_code == 200
    assert replay.status_code == 404  # single-use


def test_deny_and_listing(monkeypatch, tmp_path) -> None:
    approvals, _ = _wire(monkeypatch, tmp_path, declared=["pc.shell.run"])
    a = _pending(approvals)
    client = TestClient(app)

    listed = client.get(
        "/api/devices/approvals", headers={"Authorization": "Bearer tok-requester"}
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == a.id

    denied = client.post(
        f"/api/devices/approvals/{a.id}/deny",
        headers={"Authorization": "Bearer tok-approver"},
    )
    assert denied.status_code == 200
    assert approvals.get(a.id) is None


def test_audit_endpoint_lists_rows(monkeypatch, tmp_path) -> None:
    _, audit = _wire(monkeypatch, tmp_path, declared=["phone.battery"])
    audit.record(
        requester="r", node=NODE, skill="phone.battery", params={},
        risk=0, outcome="responded", result={"ok": True},
    )
    client = TestClient(app)

    r = client.get("/api/devices/audit", headers={"Authorization": "Bearer tok-requester"})

    assert r.status_code == 200
    assert r.json()[0]["outcome"] == "responded"
