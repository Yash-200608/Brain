"""
Jarvis Brain — Configuration.
Loads from `settings.toml` + environment.
"""
from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


_TOML = _load_toml(ROOT / "config" / "settings.toml")


def _t(section: str, key: str, default: Any) -> Any:
    return _TOML.get(section, {}).get(key, default)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JARVIS_", env_file=".env", extra="ignore")

    # API
    api_host: str = _t("api", "host", "0.0.0.0")
    api_port: int = _t("api", "port", 8000)
    # Explicit allowlist -- matches docker-compose.yml's nginx dashboard on
    # :5173 plus common local dev origins. Wildcard ("*") is never a default;
    # override via JARVIS_CORS_ORIGINS='["http://host:port", ...]' (JSON
    # array, per pydantic-settings' env parsing for list fields) for other setups.
    cors_origins: list[str] = _t("api", "cors_origins", [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:8000", "http://127.0.0.1:8000",
    ])

    # LLM
    ollama_base_url: str = _t("llm", "ollama_base_url", "http://localhost:11434")
    llm_provider: str = _t("llm", "provider", "ollama")
    planner_model: str = _t("llm", "planner_model", "llama3.1:8b")
    executor_model: str = _t("llm", "executor_model", "llama3.1:8b")
    critic_model: str = _t("llm", "critic_model", "llama3.1:8b")

    # Identity (V2 foundation — non-enforcing)
    default_user_id: str = _t("identity", "default_user_id", "owner")
    api_keys: dict[str, str] = _t("identity", "api_keys", {})
    # Approver keys (Priority #4 Milestone 10): token -> user_id, seeded
    # with SCOPE_DEVICES_APPROVE (+ devices.read). Kept separate from
    # api_keys because approval privilege must never be grantable via the
    # ordinary key list (NP-7: approvers are privileged above requesters).
    # Env: JARVIS_APPROVER_KEYS={"<token>": "owner"}
    approver_keys: dict[str, str] = _t("identity", "approver_keys", {})

    # Sessions (V2 foundation)
    max_sessions: int = _t("sessions", "max_sessions", 256)

    # Embeddings
    embedding_model: str = _t("embeddings", "model", "sentence-transformers/all-MiniLM-L6-v2")
    reranker_model: str = _t("embeddings", "reranker", "cross-encoder/ms-marco-MiniLM-L-6-v2")

    # Memory
    memory_top_k: int = _t("memory", "top_k", 8)
    memory_overshoot: int = _t("memory", "overshoot", 3)
    chroma_path: str = str(DATA_DIR / "chroma_db")

    # Retrieval scoring
    weight_semantic: float = _t("retrieval", "weight_semantic", 0.55)
    weight_keyword: float = _t("retrieval", "weight_keyword", 0.15)
    weight_importance: float = _t("retrieval", "weight_importance", 0.10)
    weight_access: float = _t("retrieval", "weight_access", 0.10)
    weight_recency: float = _t("retrieval", "weight_recency", 0.10)

    # Critic
    critic_confidence_threshold: float = _t("critic", "confidence_threshold", 0.65)
    max_retries: int = _t("critic", "max_retries", 2)

    # Storage
    goals_db: str = str(DATA_DIR / "goals.db")
    sessions_db: str = str(DATA_DIR / "sessions.db")
    devices_db: str = str(DATA_DIR / "devices.db")

    # Logging
    log_level: str = _t("logging", "level", "INFO")
    log_dir: str = str(DATA_DIR / "logs")

    # MQTT (Priority #3 Milestone 2 -- dormant by default)
    mqtt_enabled: bool = _t("mqtt", "enabled", False)
    mqtt_host: str = _t("mqtt", "host", "127.0.0.1")
    mqtt_port: int = _t("mqtt", "port", 1883)
    mqtt_client_id: str = _t("mqtt", "client_id", "brain")
    mqtt_keepalive: int = _t("mqtt", "keepalive", 30)
    mqtt_qos: int = _t("mqtt", "qos", 1)
    mqtt_username: str | None = _t("mqtt", "username", None)
    mqtt_password: str | None = _t("mqtt", "password", None)
    mqtt_hmac_key: str | None = _t("mqtt", "hmac_key", None)


settings = Settings()
os.makedirs(settings.chroma_path, exist_ok=True)
os.makedirs(settings.log_dir, exist_ok=True)
