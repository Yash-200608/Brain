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
