"""Shared test fixtures.

Test isolation note: `config.Settings` is instantiated once, at module import
time, which happens during pytest collection — after this conftest is imported
but before any fixture runs. Environment overrides must therefore be applied
here at import time; a function-scoped monkeypatch fixture would run too late
to have any effect on `config.settings`.
"""
from __future__ import annotations

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="jarvis_test_data_")
os.environ.setdefault("JARVIS_GOALS_DB", os.path.join(_TMP, "goals.db"))
os.environ.setdefault("JARVIS_SESSIONS_DB", os.path.join(_TMP, "sessions.db"))
os.environ.setdefault("JARVIS_CHROMA_PATH", os.path.join(_TMP, "chroma"))
os.environ.setdefault("JARVIS_DEVICES_DB", os.path.join(_TMP, "devices.db"))

# Priority #3 Milestone 12 added a real JARVIS_MQTT_ENABLED=true / hmac key
# to the local dev .env for the live end-to-end demo. Actual OS env vars
# take precedence over .env for pydantic-settings, so without this override
# the whole suite would inherit "mqtt really enabled" as its default and
# tests written against the documented default (disabled) -- e.g.
# test_full_app_starts_and_health_responds_with_mqtt_disabled -- would
# instead attempt a real broker connection via the real app lifespan.
# Individual tests that want the enabled path already monkeypatch
# settings.mqtt_enabled explicitly (test_mqtt_lifespan.py) and are
# unaffected by this.
os.environ.setdefault("JARVIS_MQTT_ENABLED", "false")
os.environ.setdefault("JARVIS_MQTT_HMAC_KEY", "")
