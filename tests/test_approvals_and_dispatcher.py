"""Priority #4 Milestone 7 -- ApprovalStore (the three NP-7 properties) and
DeviceDispatcher (NP-5 live-declaration enforcement + audit trail), via
tempfile-backed stores and the established fake-broker technique.
"""

from __future__ import annotations

import asyncio
import json
import tempfile

from devices.approvals import ApprovalStore, principal_key
from devices.audit import DispatchAudit
from devices.dispatcher import DeviceDispatcher
from devices.store import DeviceStore
from mqtt.client import BrainMqttClient
from mqtt import set_mqtt_client
from protocols.chimera_contract import ChimeraEnvelope, sign

KEY = "f" * 64
REQUESTER = principal_key("owner", "api", "key-aaa")
APPROVER = principal_key("owner", "api", "key-bbb")


def _db() -> str:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return f.name


def teardown_function() -> None:
    set_mqtt_client(None)


# ---------------------------------------------------------------------- #
# ApprovalStore -- NP-7                                                    #
# ---------------------------------------------------------------------- #


def test_approval_single_use(tmp_path=None) -> None:
    store = ApprovalStore(db_path=_db())
    a = store.request("pc", "pc.shell.run", {"command": "x"}, 2, REQUESTER)

    first = store.consume(a.id, APPROVER)
    second = store.consume(a.id, APPROVER)

    assert first is not None and first.id == a.id
    assert second is None  # property 3: single-use


def test_same_principal_cannot_approve_and_approval_survives() -> None:
    """Property 1: the requester approving via a *different request* is
    still the same principal -- rejected, and the approval is NOT burned
    (a genuinely distinct approver can still act on it)."""
    store = ApprovalStore(db_path=_db())
    a = store.request("pc", "pc.shell.run", {"command": "x"}, 2, REQUESTER)

    assert store.consume(a.id, REQUESTER) is None
    assert store.get(a.id) is not None  # still pending
    assert store.consume(a.id, APPROVER) is not None


def test_approval_is_instance_bound_via_stored_action() -> None:
    """Property 2/3: consume() returns the STORED (node, skill, params) --
    the executing caller dispatches exactly that, so an approval can never
    apply to a different action instance."""
    store = ApprovalStore(db_path=_db())
    a = store.request("pc", "pc.shell.run", {"command": "echo safe"}, 2, REQUESTER)

    consumed = store.consume(a.id, APPROVER)

    assert consumed.params == {"command": "echo safe"}
    assert consumed.risk == 2


def test_deny_removes_pending() -> None:
    store = ApprovalStore(db_path=_db())
    a = store.request("pc", "pc.shell.run", {"command": "x"}, 2, REQUESTER)

    assert store.deny(a.id) is True
    assert store.get(a.id) is None
    assert store.deny(a.id) is False


def test_pending_approvals_survive_restart() -> None:
    db = _db()
    ApprovalStore(db_path=db).request("pc", "pc.shell.run", {"command": "x"}, 2, REQUESTER)

    reopened = ApprovalStore(db_path=db)

    assert len(reopened.list_pending()) == 1


# ---------------------------------------------------------------------- #
# DeviceDispatcher -- NP-5 + audit                                         #
# ---------------------------------------------------------------------- #


def _dispatcher_with_node(skills: list[str] | None) -> tuple[DeviceDispatcher, DeviceStore, DispatchAudit]:
    db = _db()
    store = DeviceStore(db_path=db)
    if skills is not None:
        store.record_capabilities("jarvis-core-pc", skills)
    else:
        store.mark_seen("jarvis-core-pc")
    audit = DispatchAudit(db_path=db)
    return DeviceDispatcher(store=store, audit=audit), store, audit


def _client_with_responder(action: str, params: dict) -> BrainMqttClient:
    client = BrainMqttClient(host="localhost", port=1883, client_id="test")

    class _FakeMsg:
        def __init__(self, topic, payload):
            self.topic = topic
            self.payload = payload

    class _FakeMessages:
        def __init__(self, msgs):
            self._msgs = msgs

        def __aiter__(self):
            return self._gen()

        async def _gen(self):
            for m in self._msgs:
                yield m

    class _FakeAiomqttClient:
        def __init__(self, messages):
            self.messages = messages

    async def fake_publish(topic, payload, *, qos=None, retain=False):
        if not topic.endswith("/cmd"):
            return
        response = ChimeraEnvelope(
            node="jarvis-core-pc", verb="response", action=action,
            params=params, request_id=payload.get("request_id"),
        )
        data = json.dumps(sign(response, KEY).model_dump(), separators=(",", ":")).encode()
        await client._dispatch_loop(
            _FakeAiomqttClient(_FakeMessages([_FakeMsg("chimera/jarvis-core-pc/response", data)]))
        )

    client.publish = fake_publish  # type: ignore[method-assign]
    return client


def test_undeclared_skill_rejected_and_audited() -> None:
    dispatcher, _, audit = _dispatcher_with_node(["phone.battery"])

    outcome = asyncio.run(
        dispatcher.dispatch(
            node="jarvis-core-pc", skill="pc.shell.run", params={}, risk=2,
            requester=REQUESTER, key=KEY,
        )
    )

    assert outcome.ok is False
    assert "does not declare" in outcome.detail
    rows = audit.list()
    assert rows[0]["outcome"] == "rejected_undeclared_skill"


def test_node_with_no_declarations_rejects_everything_but_ping() -> None:
    dispatcher, _, _ = _dispatcher_with_node(None)

    outcome = asyncio.run(
        dispatcher.dispatch(
            node="jarvis-core-pc", skill="phone.battery", params={}, risk=0,
            requester=REQUESTER, key=KEY,
        )
    )

    assert outcome.ok is False


def test_unknown_node_rejected() -> None:
    dispatcher, _, audit = _dispatcher_with_node(["phone.battery"])

    outcome = asyncio.run(
        dispatcher.dispatch(
            node="ghost", skill="phone.battery", params={}, risk=0,
            requester=REQUESTER, key=KEY,
        )
    )

    assert outcome.ok is False
    assert audit.list()[0]["outcome"] == "rejected_unknown_node"


def test_declared_skill_dispatches_and_audits_result() -> None:
    dispatcher, _, audit = _dispatcher_with_node(["phone.battery"])
    set_mqtt_client(_client_with_responder("phone.battery", {"ok": True, "battery": {"level": 42}}))

    outcome = asyncio.run(
        dispatcher.dispatch(
            node="jarvis-core-pc", skill="phone.battery", params={}, risk=0,
            requester=REQUESTER, key=KEY, timeout=2.0,
        )
    )

    assert outcome.ok is True
    assert outcome.result == {"ok": True, "battery": {"level": 42}}
    row = audit.list()[0]
    assert row["outcome"] == "responded"
    assert row["result"] == {"ok": True, "battery": {"level": 42}}
    assert row["requester"] == REQUESTER


def test_resolve_node_uses_live_declarations() -> None:
    dispatcher, store, _ = _dispatcher_with_node(["phone.battery"])

    assert dispatcher.resolve_node("phone.battery") == "jarvis-core-pc"
    assert dispatcher.resolve_node("pc.shell.run") is None

    # NP-5's removal property: retract the declaration, resolution follows.
    store.record_capabilities("jarvis-core-pc", [])
    assert dispatcher.resolve_node("phone.battery") is None
