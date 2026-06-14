"""ChromaMemoryStore — vector + metadata persistence."""
from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Sequence
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import settings

logger = logging.getLogger(__name__)


class ChromaMemoryStore:
    """Wraps ChromaDB. Embeddings are computed with `EmbeddingProvider`."""

    COLLECTION = "jarvis_memory"

    def __init__(self, path: str | None = None) -> None:
        # Deferred import: a module-level import would trigger
        # models/__init__ → models.classifier → agents/__init__ →
        # agents.memory_agent → memory.store (this module, partially
        # initialised) and crash any import path that reaches `memory`
        # before `agents` — including the `api.server` entry point.
        from models.embeddings import EmbeddingProvider

        self.client = chromadb.PersistentClient(
            path=path or settings.chroma_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(self.COLLECTION)
        self.embedder = EmbeddingProvider()

    # -- writes --
    def add(self, text: str, *, importance: float = 0.5, metadata: dict | None = None) -> str:
        mem_id = uuid.uuid4().hex
        meta: dict[str, Any] = {
            "importance": float(importance),
            "created_at": time.time(),
            "access_count": 0,
            "last_accessed": time.time(),
        }
        # Chroma metadata values must be scalar — serialise anything else.
        for k, v in (metadata or {}).items():
            meta[str(k)] = v if isinstance(v, (str, int, float, bool)) else json.dumps(v)
        emb: Sequence[float] = self.embedder.embed([text])[0]
        self.collection.add(ids=[mem_id], documents=[text], metadatas=[meta], embeddings=[emb])
        return mem_id

    # -- reads --
    def query(self, query: str, top_k: int = 8, *, where: dict | None = None) -> list[dict]:
        """Vector search. ``where`` is an optional Chroma metadata filter —
        the hook scoped (multi-user) retrieval builds on."""
        emb: Sequence[float] = self.embedder.embed([query])[0]
        res = self.collection.query(query_embeddings=[emb], n_results=top_k, where=where)
        docs = (res.get("documents") or [[]])[0]
        ids = (res.get("ids") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        out: list[dict] = []
        for i, doc in enumerate(docs):
            out.append(
                {
                    "id": ids[i],
                    "text": doc,
                    "metadata": dict(metas[i]) if i < len(metas) else {},
                    "distance": float(dists[i]) if i < len(dists) else 0.0,
                }
            )
        return out

    def touch(self, mem_id: str) -> None:
        """Mark this memory as accessed (for recency / access boost)."""
        try:
            existing = self.collection.get(ids=[mem_id], include=["metadatas"])
            metas = existing.get("metadatas") or []
            if not metas:
                return
            meta = dict(metas[0] or {})
            count = meta.get("access_count", 0)
            meta["access_count"] = (int(count) if isinstance(count, (int, float, str)) else 0) + 1
            meta["last_accessed"] = time.time()
            self.collection.update(ids=[mem_id], metadatas=[meta])
        except Exception as e:  # noqa: BLE001
            logger.debug("touch failed for %s: %s", mem_id, e)

    def all(self) -> list[dict]:
        res = self.collection.get(include=["documents", "metadatas"])
        return [
            {"id": i, "text": d, "metadata": m}
            for i, d, m in zip(res.get("ids") or [], res.get("documents") or [], res.get("metadatas") or [])
        ]
