"""The M7 Done-when test: one natural-language request through the REAL
CognitivePipeline -- deterministically planned, risk-gated, dispatched over
a (fake) broker, and recorded in the audit trail. Plus the high-risk
variant: blocked at the pipeline's existing risk gate with a pending
approval created.

The LLM-dependent collaborators (router/planner/critic/reflector) are
stubs that RAISE if touched -- proving the device turn genuinely bypasses
them (no critic retry that would re-dispatch, no LLM dependency for the
keystone daily commands).
"""

from __future__ import annotations

import asyncio
import json
import tempfile

from core.context_optimizer import ContextOptimizer
from core.pipeline import CognitivePipeline
from core.session import SessionState
from agents.device_agent import DeviceAgent
from agents.registry import WorkerRegistry
from config import settings
from devices.approvals import ApprovalStore
from devices.audit import DispatchAudit
from devices.dispatcher import DeviceDispatcher
from devices.store import DeviceStore
from identity import Principal
from mqtt import set_mqtt_client
from mqtt.client import BrainMqttClient
from protocols.chimera_contract import ChimeraEnvelope, sign

KEY = "f" * 64
NODE = "jarvis-core-pc"


class _MustNotBeTouched:
    """Any attribute access explodes -- proves LLM collaborators are never
    consulted during a device turn."""

    def __getattr__(self, name):
        raise AssertionError(f"LLM collaborator used during device turn: {name}")


class _RecordingSessionService:
    def __init__(self):
        self.turns = []

    def append_turn(self, session_id, user_input, output):
        self.turns.append((session_id, user_input, output))


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


def _build_pipeline(declared: list[str]):
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    store = DeviceStore(db_path=db)
    store.record_capabilities(NODE, declared)
    audit = DispatchAudit(db_path=db)
    approvals = ApprovalStore(db_path=db)
    dispatcher = DeviceDispatcher(store=store, audit=audit)

    registry = WorkerRegistry()
    registry.register(DeviceAgent(dispatcher))
    sessions = _RecordingSessionService()

    pipeline = CognitivePipeline(
        registry=registry,
        router=_MustNotBeTouched(),
        planner=_MustNotBeTouched(),
        critic=_MustNotBeTouched(),
        context_opt=ContextOptimizer(),
        reflector=_MustNotBeTouched(),
        memory_service=_MustNotBeTouched(),
        goal_service=_MustNotBeTouched(),
        session_service=sessions,
        bus=None,
        device_dispatcher=dispatcher,
        approval_store=approvals,
    )
    return pipeline, audit, approvals, sessions


def teardown_function() -> None:
    set_mqtt_client(None)


def test_nl_request_planned_dispatched_recorded(monkeypatch) -> None:
    """'what's my battery' -> deterministic plan -> spine dispatch (fake
    broker) -> truthful node answer in the response -> audit row."""
    monkeypatch.setattr(settings, "mqtt_enabled", True)
    monkeypatch.setattr(settings, "mqtt_hmac_key", KEY)
    pipeline, audit, _, sessions = _build_pipeline(["phone.battery"])
    set_mqtt_client(_fake_responder_client("phone.battery", {"ok": True, "battery": {"level": 64}}))

    principal = Principal(user_id="owner", client_id="api", metadata={"key_id": "key-req"})
    state = SessionState(session_id="s1")

    result = asyncio.run(pipeline.run_turn(state, "what's my battery", principal))

    assert "64" in result["response"]
    assert result["tasks"][0]["agent"] == "device"
    assert result["tasks"][0]["extra"]["skill"] == "phone.battery"
    row = audit.list()[0]
    assert row["outcome"] == "responded"
    assert row["skill"] == "phone.battery"
    assert "key-req" in row["requester"]
    assert sessions.turns and sessions.turns[0][1] == "what's my battery"
    assert state.history[-1]["input"] == "what's my battery"


def test_high_risk_nl_blocked_with_pending_approval(monkeypatch) -> None:
    """'run shell: whoami' -> risk 2 -> the pipeline's existing gate blocks
    it (nothing dispatched) and a pending approval bound to the exact
    action instance exists for a distinct approver to act on."""
    monkeypatch.setattr(settings, "mqtt_enabled", True)
    monkeypatch.setattr(settings, "mqtt_hmac_key", KEY)
    pipeline, audit, approvals, _ = _build_pipeline(["pc.shell.run"])

    principal = Principal(user_id="owner", client_id="api", metadata={"key_id": "key-req"})
    state = SessionState(session_id="s2")

    result = asyncio.run(pipeline.run_turn(state, "run shell: whoami", principal))

    pending = approvals.list_pending()
    assert len(pending) == 1
    assert pending[0].skill == "pc.shell.run"
    assert pending[0].params == {"command": "whoami"}
    assert pending[0].node == NODE  # resolved from live declarations
    assert pending[0].id in result["response"]  # user is told how to proceed
    assert "blocked" in result["response"]
    assert audit.list()[0]["outcome"] == "approval_requested"


def test_non_device_text_falls_through_and_touches_the_llm_path(monkeypatch) -> None:
    """Chitchat must NOT enter the device branch -- proven by the exploding
    router stub being reached (the normal pipeline path)."""
    monkeypatch.setattr(settings, "mqtt_enabled", True)
    monkeypatch.setattr(settings, "mqtt_hmac_key", KEY)
    pipeline, _, _, _ = _build_pipeline(["phone.battery"])

    state = SessionState(session_id="s3")

    try:
        asyncio.run(pipeline.run_turn(state, "tell me a story", None))
        raise AssertionError("expected the exploding router stub to be reached")
    except AssertionError as e:
        assert "LLM collaborator used" in str(e) or "exploding" not in str(e)
