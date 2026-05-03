"""/api/memory routes."""
from __future__ import annotations

from fastapi import APIRouter

from api.schemas import MemorySearchIn, MemoryWriteIn
from memory.retriever import MemoryRetriever
from memory.writer import MemoryWriter

router = APIRouter()
_retriever = MemoryRetriever()
_writer = MemoryWriter()


@router.post("/search")
def search(payload: MemorySearchIn) -> list[dict]:
    return _retriever.search(payload.query, top_k=payload.top_k)


@router.post("/write")
def write(payload: MemoryWriteIn) -> dict:
    mid = _writer.write(payload.text, importance=payload.importance, metadata=payload.metadata)
    return {"id": mid}
