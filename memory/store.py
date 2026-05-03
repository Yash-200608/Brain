"""ChromaMemoryStore — vector + metadata persistence."""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import settings
from models.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)


class ChromaMemoryStore:
    """Wraps ChromaDB. Embeddings are computed with `EmbeddingProvider`."""

    COLLECTION = "jarvis_memory"

    def __init__(self, path: str | None = None) -> None:
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
        meta.update(metadata or {})
        emb = self.embedder.embed([text])[0]
        self.collection.add(ids=[mem_id], documents=[text], metadatas=[meta], embeddings=[emb])
        return mem_id

    # -- reads --
    def query(self, query: str, top_k: int = 8) -> list[dict]:
        emb = self.embedder.embed([query])[0]
        res = self.collection.query(query_embeddings=[emb], n_results=top_k)
        out: list[dict] = []
        for i, doc in enumerate(res.get("documents", [[]])[0]):
            out.append(
                {
                    "id": res["ids"][0][i],
                    "text": doc,
                    "metadata": res["metadatas"][0][i],
                    "distance": res["distances"][0][i] if "distances" in res else 0.0,
                }
            )
        return out

    def touch(self, mem_id: str) -> None:
        """Mark this memory as accessed (for recency / access boost)."""
        try:
            existing = self.collection.get(ids=[mem_id], include=["metadatas"])
            if not existing.get("metadatas"):
                return
            meta = existing["metadatas"][0] or {}
            meta["access_count"] = int(meta.get("access_count", 0)) + 1
            meta["last_accessed"] = time.time()
            self.collection.update(ids=[mem_id], metadatas=[meta])
        except Exception as e:  # noqa: BLE001
            logger.debug("touch failed for %s: %s", mem_id, e)

    def all(self) -> list[dict]:
        res = self.collection.get(include=["documents", "metadatas"])
        return [
            {"id": i, "text": d, "metadata": m}
            for i, d, m in zip(res.get("ids", []), res.get("documents", []), res.get("metadatas", []))
        ]
