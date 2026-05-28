from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from app.core import config

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class VectorRecord:
    vector_id: str
    doc_id: str
    chunk_id: str
    embedding: list[float]
    text: str
    metadata: dict[str, Any]


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._store: dict[str, dict[str, dict[str, VectorRecord]]] = defaultdict(lambda: defaultdict(dict))

    async def upsert(self, *, tenant_id: str, namespace: str, record: VectorRecord) -> None:
        self._store[tenant_id][namespace][record.vector_id] = record

    async def delete_document(self, *, tenant_id: str, namespace: str, doc_id: str) -> int:
        records = self._store[tenant_id][namespace]
        to_delete = [rid for rid, value in records.items() if value.doc_id == doc_id]
        for rid in to_delete:
            del records[rid]
        return len(to_delete)

    async def search(
        self,
        *,
        tenant_id: str,
        namespace: str,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[VectorRecord, float]]:
        filters = filters or {}
        records = self._store[tenant_id][namespace].values()
        scored: list[tuple[VectorRecord, float]] = []
        for record in records:
            if not self._match_filters(record.metadata, filters):
                continue
            score = self._cosine_similarity(query_embedding, record.embedding)
            if score <= 0:
                continue
            scored.append((record, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[: max(1, top_k)]

    def _match_filters(self, metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
        return all(metadata.get(key) == value for key, value in filters.items())

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)


class VectorStoreAdapter:
    """Thin gateway: vector search/RAG for knowledge APIs uses in-process memory only."""

    def __init__(self) -> None:
        self._memory = InMemoryVectorStore()
        self._configured_provider = (config.VECTOR_STORE_PROVIDER or "memory").strip().lower() or "memory"
        if self._configured_provider == "qdrant":
            logger.warning(
                "VECTOR_STORE_PROVIDER=qdrant is ignored on the thin gateway; "
                "using in-memory store. Use domain bots for Qdrant-backed RAG."
            )
        self._active: Any = self._memory
        self._fallback_used = self._configured_provider == "qdrant"

    @property
    def configured_provider(self) -> str:
        return "memory"

    @property
    def backend_name(self) -> str:
        return self._active.__class__.__name__

    @property
    def fallback_used(self) -> bool:
        return self._fallback_used

    async def upsert(self, *, tenant_id: str, namespace: str, record: VectorRecord) -> None:
        await self._memory.upsert(tenant_id=tenant_id, namespace=namespace, record=record)

    async def delete_document(self, *, tenant_id: str, namespace: str, doc_id: str) -> int:
        return int(await self._memory.delete_document(tenant_id=tenant_id, namespace=namespace, doc_id=doc_id))

    async def search(
        self,
        *,
        tenant_id: str,
        namespace: str,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[VectorRecord, float]]:
        return await self._memory.search(
            tenant_id=tenant_id,
            namespace=namespace,
            query_embedding=query_embedding,
            top_k=top_k,
            filters=filters,
        )


vector_store = VectorStoreAdapter()
