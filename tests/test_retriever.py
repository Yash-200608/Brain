from memory.retriever import MemoryRetriever


def test_dedupe_removes_dup_text():
    items = [
        {"text": "hello world", "metadata": {}, "score": 0.9, "id": "a"},
        {"text": "hello world", "metadata": {}, "score": 0.5, "id": "b"},
        {"text": "different", "metadata": {}, "score": 0.4, "id": "c"},
    ]
    out = MemoryRetriever._dedupe(items)
    assert len(out) == 2
