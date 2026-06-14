from events import EventBus, MemoryWritten
from identity import Principal
from services import MemoryService


class FakeMemoryAgent:
    def __init__(self):
        self.writes = []
        self.searches = []

    def write(self, text, *, importance=0.5, metadata=None):
        self.writes.append({"text": text, "importance": importance, "metadata": metadata})
        return "mem-1"

    def search(self, query, top_k=None, *, where=None):
        self.searches.append({"query": query, "top_k": top_k, "where": where})
        return [{"id": "m1", "text": "hit"}]


def test_write_injects_scope_metadata():
    agent = FakeMemoryAgent()
    svc = MemoryService(agent)  # type: ignore[arg-type]
    svc.write("hello", principal=Principal(user_id="alice"), session_id="s1", origin="api")
    meta = agent.writes[0]["metadata"]
    assert meta["user_id"] == "alice"
    assert meta["visibility"] == "private"
    assert meta["session_id"] == "s1"
    assert meta["origin"] == "api"
    assert meta["trust_level"] == "standard"


def test_write_defaults_to_owner_without_principal():
    agent = FakeMemoryAgent()
    svc = MemoryService(agent)  # type: ignore[arg-type]
    svc.write("hello")
    meta = agent.writes[0]["metadata"]
    assert meta["user_id"] == "owner"
    assert "session_id" not in meta
    assert "origin" not in meta


def test_write_does_not_clobber_explicit_metadata():
    agent = FakeMemoryAgent()
    svc = MemoryService(agent)  # type: ignore[arg-type]
    svc.write("x", metadata={"user_id": "explicit", "source": "reflection"},
              principal=Principal(user_id="alice"))
    meta = agent.writes[0]["metadata"]
    assert meta["user_id"] == "explicit"
    assert meta["source"] == "reflection"


def test_write_emits_memory_written_event():
    agent = FakeMemoryAgent()
    bus = EventBus()
    seen = []
    bus.subscribe(MemoryWritten.TYPE, seen.append)
    svc = MemoryService(agent, bus=bus)  # type: ignore[arg-type]
    svc.write("hello", principal=Principal(user_id="alice"), session_id="s1")
    assert len(seen) == 1
    assert seen[0].memory_id == "mem-1"
    assert seen[0].user_id == "alice"
    assert seen[0].session_id == "s1"


def test_search_delegates_with_where():
    agent = FakeMemoryAgent()
    svc = MemoryService(agent)  # type: ignore[arg-type]
    out = svc.search("query", top_k=3, where={"user_id": "alice"})
    assert out[0]["id"] == "m1"
    assert agent.searches[0] == {"query": "query", "top_k": 3, "where": {"user_id": "alice"}}
