"""Route-level tests for /api/devices (through AuthMiddleware + the real
FastAPI app), Priority #3 Milestone 9 (read-only routes) and Milestone 12
(POST /{node}/ping).
"""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

from api.routes import devices as devices_route
from api.server import app
from config import settings
from devices.store import DeviceStore
from identity import IdentityService, set_identity_service
from mqtt.client import BrainMqttClient, set_mqtt_client
from protocols.chimera_contract import ChimeraEnvelope, sign

KEY = "f" * 64
NODE = "jarvis-core-pc"


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


def _make_client_with_simulated_responder(response_builder):
    """Ported from test_mqtt_signed_command.py: a BrainMqttClient whose
    publish() -- when publishing to a /cmd topic -- synthesizes a response
    and feeds it through the real _dispatch_loop(), proving the route
    exercises the real send_command_and_await_response() wiring, not a
    shortcut."""
    client = BrainMqttClient(host="localhost", port=1883, client_id="test")

    async def fake_publish(topic, payload, *, qos=None, retain=False):
        if not topic.endswith("/cmd"):
            return
        response_payload = response_builder(payload)
        if response_payload is None:
            return
        data = json.dumps(response_payload, separators=(",", ":")).encode()
        fake_aiomqtt = _FakeAiomqttClient(
            _FakeMessages([_FakeMsg(f"chimera/{NODE}/response", data)])
        )
        await client._dispatch_loop(fake_aiomqtt)

    client.publish = fake_publish  # type: ignore[method-assign]
    return client


def teardown_function() -> None:
    set_identity_service(None)
    set_mqtt_client(None)


def test_list_devices_requires_auth() -> None:
    set_identity_service(IdentityService(api_keys={"tok": "owner"}))
    client = TestClient(app)

    r = client.get("/api/devices/")

    assert r.status_code == 401


def test_list_devices_empty(monkeypatch, tmp_path) -> None:
    set_identity_service(IdentityService(api_keys={"tok": "owner"}))
    monkeypatch.setattr(devices_route, "_store", DeviceStore(db_path=str(tmp_path / "d.db")))
    client = TestClient(app)

    r = client.get("/api/devices/", headers={"Authorization": "Bearer tok"})

    assert r.status_code == 200
    assert r.json() == []


def test_list_devices_with_devices_present(monkeypatch, tmp_path) -> None:
    set_identity_service(IdentityService(api_keys={"tok": "owner"}))
    store = DeviceStore(db_path=str(tmp_path / "d.db"))
    store.record_state("pc-main", {"cpu": 12})
    monkeypatch.setattr(devices_route, "_store", store)
    client = TestClient(app)

    r = client.get("/api/devices/", headers={"Authorization": "Bearer tok"})

    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["node"] == "pc-main"


def test_get_device_known_node_round_trips_state_and_online(monkeypatch, tmp_path) -> None:
    set_identity_service(IdentityService(api_keys={"tok": "owner"}))
    store = DeviceStore(db_path=str(tmp_path / "d.db"))
    store.record_state("node-a", {"battery": 80})
    monkeypatch.setattr(devices_route, "_store", store)
    client = TestClient(app)

    r = client.get("/api/devices/node-a", headers={"Authorization": "Bearer tok"})

    assert r.status_code == 200
    body = r.json()
    assert body["node"] == "node-a"
    assert body["state"] == {"battery": 80}
    assert body["is_online"] is True


def test_get_device_unknown_node_returns_404(monkeypatch, tmp_path) -> None:
    set_identity_service(IdentityService(api_keys={"tok": "owner"}))
    monkeypatch.setattr(devices_route, "_store", DeviceStore(db_path=str(tmp_path / "d.db")))
    client = TestClient(app)

    r = client.get("/api/devices/does-not-exist", headers={"Authorization": "Bearer tok"})

    assert r.status_code == 404


def test_ping_requires_auth() -> None:
    set_identity_service(IdentityService(api_keys={"tok": "owner"}))
    client = TestClient(app)

    r = client.post(f"/api/devices/{NODE}/ping")

    assert r.status_code == 401


def test_ping_returns_503_when_mqtt_not_enabled(monkeypatch) -> None:
    set_identity_service(IdentityService(api_keys={"tok": "owner"}))
    monkeypatch.setattr(settings, "mqtt_enabled", False)
    client = TestClient(app)

    r = client.post(f"/api/devices/{NODE}/ping", headers={"Authorization": "Bearer tok"})

    assert r.status_code == 503


def test_ping_returns_503_when_hmac_key_missing(monkeypatch) -> None:
    set_identity_service(IdentityService(api_keys={"tok": "owner"}))
    monkeypatch.setattr(settings, "mqtt_enabled", True)
    monkeypatch.setattr(settings, "mqtt_hmac_key", None)
    client = TestClient(app)

    r = client.post(f"/api/devices/{NODE}/ping", headers={"Authorization": "Bearer tok"})

    assert r.status_code == 503


def test_ping_happy_path_returns_verified_response(monkeypatch) -> None:
    set_identity_service(IdentityService(api_keys={"tok": "owner"}))
    monkeypatch.setattr(settings, "mqtt_enabled", True)
    monkeypatch.setattr(settings, "mqtt_hmac_key", KEY)

    def build(cmd_payload):
        response = ChimeraEnvelope(node=NODE, verb="response", action="ping", params={"pong": True})
        return sign(response, KEY).model_dump()

    set_mqtt_client(_make_client_with_simulated_responder(build))
    client = TestClient(app)

    r = client.post(f"/api/devices/{NODE}/ping", headers={"Authorization": "Bearer tok"})

    assert r.status_code == 200
    body = r.json()
    assert body["node"] == NODE
    assert body["result"] == {"pong": True}


def test_ping_returns_504_on_timeout(monkeypatch) -> None:
    """The route hardcodes a 10s timeout on the real
    send_command_and_await_response() call -- already proven fast-failing
    at the function level by test_mqtt_signed_command.py's own
    short-timeout tests. Here, monkeypatch the route's bound name to a
    stub that resolves to None immediately, so this test only proves the
    route's None -> 504 mapping, not the timeout mechanics themselves."""
    set_identity_service(IdentityService(api_keys={"tok": "owner"}))
    monkeypatch.setattr(settings, "mqtt_enabled", True)
    monkeypatch.setattr(settings, "mqtt_hmac_key", KEY)

    async def _never_responds(*args, **kwargs):
        return None

    monkeypatch.setattr(devices_route, "send_command_and_await_response", _never_responds)
    set_mqtt_client(_make_client_with_simulated_responder(lambda cmd_payload: None))
    client = TestClient(app)

    r = client.post(f"/api/devices/{NODE}/ping", headers={"Authorization": "Bearer tok"})

    assert r.status_code == 504
