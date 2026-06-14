import asyncio
import threading
import time

from core.manager import SessionManager
from core.session import SessionActor, SessionState


class FakePipeline:
    """Pipeline stub: records calls, optionally dwells to expose concurrency."""

    def __init__(self, dwell: float = 0.0):
        self.dwell = dwell
        self.calls: list[tuple[str, str]] = []
        self._active = 0
        self.max_active = 0
        self._gauge = threading.Lock()

    async def run_turn(self, state: SessionState, user_input: str, principal=None):
        with self._gauge:
            self._active += 1
            self.max_active = max(self.max_active, self._active)
        try:
            if self.dwell:
                await asyncio.sleep(self.dwell)
            self.calls.append((state.session_id, user_input))
            state.history.append({"input": user_input, "output": f"ok:{user_input}"})
            return {
                "session_id": state.session_id,
                "response": f"ok:{user_input}",
                "memory_used": [],
                "tasks": [],
            }
        finally:
            with self._gauge:
                self._active -= 1


def test_same_session_accumulates_history():
    mgr = SessionManager(FakePipeline())
    r1 = mgr.handle_turn("one", session_id="s1")
    r2 = mgr.handle_turn("two", session_id="s1")
    assert r1["session_id"] == r2["session_id"] == "s1"
    actor = mgr.get("s1")
    assert actor is not None
    assert [h["input"] for h in actor.state.history] == ["one", "two"]


def test_sessions_are_isolated():
    mgr = SessionManager(FakePipeline())
    mgr.handle_turn("alpha", session_id="a")
    mgr.handle_turn("beta", session_id="b")
    actor_a, actor_b = mgr.get("a"), mgr.get("b")
    assert actor_a is not None and actor_b is not None
    assert len(actor_a.state.history) == 1
    assert len(actor_b.state.history) == 1
    assert actor_a.state.history[0]["input"] == "alpha"
    assert actor_b.state.history[0]["input"] == "beta"


def test_generated_session_id_when_omitted():
    mgr = SessionManager(FakePipeline())
    r = mgr.handle_turn("hello")
    assert r["session_id"]
    assert mgr.get(r["session_id"]) is not None


def test_distinct_sessions_run_concurrently():
    """The V1 global lock is gone: two sessions overlap in time."""
    pipeline = FakePipeline(dwell=0.15)
    mgr = SessionManager(pipeline)
    threads = [
        threading.Thread(target=mgr.handle_turn, args=(f"q{i}",), kwargs={"session_id": f"s{i}"})
        for i in range(3)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert pipeline.max_active >= 2


def test_same_session_turns_are_serialized():
    pipeline = FakePipeline(dwell=0.1)
    mgr = SessionManager(pipeline)
    threads = [
        threading.Thread(target=mgr.handle_turn, args=(f"q{i}",), kwargs={"session_id": "only"})
        for i in range(3)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert pipeline.max_active == 1
    actor = mgr.get("only")
    assert actor is not None
    assert len(actor.state.history) == 3


def test_async_entrypoint():
    mgr = SessionManager(FakePipeline())

    async def go():
        return await mgr.ahandle_turn("via-async", session_id="as1")

    r = asyncio.run(go())
    assert r["response"] == "ok:via-async"


def test_eviction_drops_oldest_idle_session():
    mgr = SessionManager(FakePipeline(), max_sessions=2)
    mgr.handle_turn("a", session_id="s1")
    time.sleep(0.01)
    mgr.handle_turn("b", session_id="s2")
    time.sleep(0.01)
    mgr.handle_turn("c", session_id="s3")
    ids = mgr.session_ids()
    assert "s1" not in ids
    assert "s2" in ids and "s3" in ids


def test_eviction_skips_busy_sessions():
    mgr = SessionManager(FakePipeline(), max_sessions=1)
    busy = mgr.get_or_create("busy")
    assert busy._lock.acquire(blocking=False)
    try:
        mgr.get_or_create("new")
        assert "busy" in mgr.session_ids()
        assert "new" in mgr.session_ids()
    finally:
        busy._lock.release()


def test_actor_state_carries_session_id():
    actor = SessionActor("sid-x", FakePipeline())
    assert actor.state.session_id == "sid-x"
    assert not actor.busy()
