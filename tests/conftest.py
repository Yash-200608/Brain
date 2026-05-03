"""Shared test fixtures."""
from __future__ import annotations

import os
import tempfile

import pytest


@pytest.fixture(autouse=True)
def _isolated_data(monkeypatch, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("jarvis_data")
    monkeypatch.setenv("JARVIS_GOALS_DB", str(tmp / "goals.db"))
    monkeypatch.setenv("JARVIS_SESSIONS_DB", str(tmp / "sessions.db"))
    monkeypatch.setenv("JARVIS_CHROMA_PATH", str(tmp / "chroma"))
    yield
