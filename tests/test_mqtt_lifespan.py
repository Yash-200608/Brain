"""Proves api/server.py's lifespan hook is a true no-op when
settings.mqtt_enabled is False (the default), and that existing endpoints
are unaffected either way. Zero real network activity anywhere in this
file -- every test fakes/subclasses BrainMqttClient rather than touching
aiomqtt.Client directly.
"""

from __future__ import annotations

import asyncio

from config import settings
from mqtt import set_mqtt_client
from mqtt.client import BrainMqttClient


def teardown_function() -> None:
    set_mqtt_client(None)


def test_lifespan_is_noop_when_mqtt_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mqtt_enabled", False)
    from api.server import app, lifespan

    started = {"called": False}

    class _Guard(BrainMqttClient):
        async def start(self):
            started["called"] = True

    set_mqtt_client(_Guard())

    async def run():
        async with lifespan(app):
            pass

    asyncio.run(run())
    assert started["called"] is False


def test_full_app_starts_and_health_responds_with_mqtt_disabled() -> None:
    from starlette.testclient import TestClient

    from api.server import app

    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200


def test_full_app_starts_with_mqtt_enabled_and_mocked_client(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mqtt_enabled", True)

    calls = []

    class _FakeClient(BrainMqttClient):
        async def start(self):
            calls.append("start")

        async def stop(self):
            calls.append("stop")

    set_mqtt_client(_FakeClient())

    from starlette.testclient import TestClient

    from api.server import app

    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200

    assert calls == ["start", "stop"]


def test_lifespan_subscribes_to_presence_when_enabled_and_keyed(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mqtt_enabled", True)
    monkeypatch.setattr(settings, "mqtt_hmac_key", "f" * 64)
    from api.server import app, lifespan

    subscriptions = []

    class _RecordingClient(BrainMqttClient):
        async def start(self):
            return None

        async def stop(self):
            return None

        async def subscribe(self, topic, handler):
            subscriptions.append(topic)

    set_mqtt_client(_RecordingClient())

    async def run():
        async with lifespan(app):
            pass

    asyncio.run(run())
    assert "chimera/+/presence" in subscriptions


def test_lifespan_skips_presence_subscription_when_key_missing(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mqtt_enabled", True)
    monkeypatch.setattr(settings, "mqtt_hmac_key", None)
    from api.server import app, lifespan

    subscriptions = []

    class _RecordingClient(BrainMqttClient):
        async def start(self):
            return None

        async def stop(self):
            return None

        async def subscribe(self, topic, handler):
            subscriptions.append(topic)

    set_mqtt_client(_RecordingClient())

    async def run():
        async with lifespan(app):
            pass

    asyncio.run(run())
    # All three (presence/state/capabilities) are gated on the same key --
    # an empty list proves none of them leaked through.
    assert subscriptions == []


def test_lifespan_subscribes_to_state_when_enabled_and_keyed(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mqtt_enabled", True)
    monkeypatch.setattr(settings, "mqtt_hmac_key", "f" * 64)
    from api.server import app, lifespan

    subscriptions = []

    class _RecordingClient(BrainMqttClient):
        async def start(self):
            return None

        async def stop(self):
            return None

        async def subscribe(self, topic, handler):
            subscriptions.append(topic)

    set_mqtt_client(_RecordingClient())

    async def run():
        async with lifespan(app):
            pass

    asyncio.run(run())
    assert "chimera/+/state" in subscriptions


def test_lifespan_subscribes_to_capabilities_when_enabled_and_keyed(monkeypatch) -> None:
    """Priority #4 Milestone 4: the third DeviceStore-backed subscription."""
    monkeypatch.setattr(settings, "mqtt_enabled", True)
    monkeypatch.setattr(settings, "mqtt_hmac_key", "f" * 64)
    from api.server import app, lifespan

    subscriptions = []

    class _RecordingClient(BrainMqttClient):
        async def start(self):
            return None

        async def stop(self):
            return None

        async def subscribe(self, topic, handler):
            subscriptions.append(topic)

    set_mqtt_client(_RecordingClient())

    async def run():
        async with lifespan(app):
            pass

    asyncio.run(run())
    assert "chimera/+/capabilities" in subscriptions
