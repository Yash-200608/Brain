"""The where-filter pass-through that scoped retrieval builds on."""
from memory.retriever import MemoryRetriever


class FakeStore:
    def __init__(self):
        self.queries = []

    def query(self, query, top_k=8, *, where=None):
        self.queries.append({"query": query, "top_k": top_k, "where": where})
        return [
            {"id": "a", "text": "hello world", "metadata": {"importance": 0.5}, "distance": 0.1},
        ]

    def touch(self, mem_id):
        pass


def test_search_passes_where_to_store():
    store = FakeStore()
    r = MemoryRetriever(store=store)  # type: ignore[arg-type]
    out = r.search("hello", top_k=2, where={"user_id": "alice"})
    assert store.queries[0]["where"] == {"user_id": "alice"}
    assert out and out[0]["id"] == "a"


def test_search_defaults_to_no_filter():
    store = FakeStore()
    r = MemoryRetriever(store=store)  # type: ignore[arg-type]
    r.search("hello")
    assert store.queries[0]["where"] is None
