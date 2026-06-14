"""V1 facade compatibility: same construction, same handle() surface,
same response shape — running the REAL pipeline end-to-end against a fake
model provider (no network, no embedding model)."""
import pytest

from modelgw import ModelGateway, ModelProvider, set_model_gateway


class ScriptedProvider(ModelProvider):
    """Answers per agent role, keyed off each agent's system prompt."""

    name = "scripted"

    def generate(self, *, model, system, prompt, temperature=0.2, options=None) -> str:
        if "Classify the user query" in system:
            # requires_memory False keeps the test free of the embedding model
            return '{"intent": "factual", "requires_memory": false, "complexity": "low"}'
        if "planner" in system:
            return "[]"  # no plan -> pipeline falls back to a single executor task
        if "critic" in system.lower():
            return '{"confidence": 0.9, "verdict": "ok", "reason": "fine"}'
        if "Extract durable facts" in system:
            return "[]"
        if "executor agent" in system:
            return "the answer"
        return ""


@pytest.fixture()
def orch():
    set_model_gateway(ModelGateway({"scripted": ScriptedProvider()}, default="scripted"))
    from orchestrator.orchestrator import JarvisOrchestrator

    try:
        yield JarvisOrchestrator()
    finally:
        set_model_gateway(None)


def test_handle_returns_v1_shape(orch):
    result = orch.handle("what is the answer")
    assert set(result) == {"session_id", "response", "memory_used", "tasks"}
    assert result["response"] == "the answer"
    assert result["memory_used"] == []
    assert len(result["tasks"]) == 1
    task = result["tasks"][0]
    assert task["agent"] == "executor"
    assert task["status"] == "done"


def test_default_session_is_stable(orch):
    r1 = orch.handle("first")
    r2 = orch.handle("second")
    assert r1["session_id"] == r2["session_id"]
    assert len(orch.state.history) == 2


def test_session_id_is_sticky_like_v1(orch):
    orch.handle("a")
    r2 = orch.handle("b", session_id="custom")
    r3 = orch.handle("c")  # V1: stays on the last explicit session
    assert r2["session_id"] == "custom"
    assert r3["session_id"] == "custom"
    assert orch.state.session_id == "custom"
    assert [h["input"] for h in orch.state.history] == ["b", "c"]


def test_sessions_no_longer_share_state(orch):
    orch.handle("for-a", session_id="sess-a")
    orch.handle("for-b", session_id="sess-b")
    actor_a = orch.sessions.get("sess-a")
    actor_b = orch.sessions.get("sess-b")
    assert actor_a is not None and actor_b is not None
    assert [h["input"] for h in actor_a.state.history] == ["for-a"]
    assert [h["input"] for h in actor_b.state.history] == ["for-b"]


def test_v1_attributes_still_exposed(orch):
    for attr in ("memory_store", "memory_agent", "registry", "router", "planner",
                 "critic", "context_opt", "reflector", "goal_store", "log_store", "state"):
        assert hasattr(orch, attr), f"V1 attribute {attr} missing from facade"


def test_turn_is_logged_to_session_store(orch):
    r = orch.handle("log me", session_id="logged-session")
    turns = orch.session_service.get_turns("logged-session")
    assert len(turns) == 1
    assert turns[0]["user_input"] == "log me"
    assert turns[0]["response"] == r["response"]


def test_turn_emits_lifecycle_events(orch):
    seen = []
    handler = orch.bus.subscribe("*", seen.append)
    try:
        orch.handle("emit events", session_id="evt-session")
    finally:
        orch.bus.unsubscribe("*", handler)
    types = [e.TYPE for e in seen if e.session_id == "evt-session"]
    assert types == ["turn.started", "task.started", "task.completed", "turn.completed"]
