from __future__ import annotations

import os
import re
from typing import Any

# When QDRANT_URL and QDRANT_COLLECTION are set, queries Qdrant for this bot's collection.
# Optional: QDRANT_FILTER_BY_DOMAIN=1 adds a payload filter domain == retrieve_documents(domain, ...).

_qdrant_singleton: Any = None
_qdrant_checked: bool = False
_embedder_singleton: Any = None
_embedder_checked: bool = False


def _qdrant_client():
    global _qdrant_singleton, _qdrant_checked
    if _qdrant_checked:
        return _qdrant_singleton
    _qdrant_checked = True
    url = (os.getenv("QDRANT_URL") or "").strip()
    if not url:
        return None
    try:
        from qdrant_client import QdrantClient

        api_key = os.getenv("QDRANT_API_KEY")
        _qdrant_singleton = QdrantClient(url=url, api_key=api_key or None, timeout=30)
    except Exception:
        _qdrant_singleton = None
    return _qdrant_singleton


def _embedder():
    global _embedder_singleton, _embedder_checked
    if _embedder_checked:
        return _embedder_singleton
    _embedder_checked = True
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        model = os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")
        _embedder_singleton = GoogleGenerativeAIEmbeddings(model=model, google_api_key=api_key)
    except Exception:
        _embedder_singleton = None
    return _embedder_singleton


def _domain_slug(domain: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (domain or "").strip().lower()).strip("-")
    return s or "default"


def _collection_name(domain: str) -> str:
    """
    QDRANT_COLLECTION: fixed collection for this bot (default / backward compatible).
    Or set QDRANT_COLLECTION_PREFIX (e.g. kb) to use collection `{prefix}_{domain_slug}` per domain namespace.
    """
    explicit = (os.getenv("QDRANT_COLLECTION") or "").strip()
    if explicit:
        return explicit
    prefix = (os.getenv("QDRANT_COLLECTION_PREFIX") or "").strip().rstrip("_-")
    if not prefix:
        return ""
    slug = _domain_slug(domain)
    return f"{prefix}_{slug}"


def retrieve_documents(domain: str, query: str, tenant_id: str | None = None) -> str:
    client = _qdrant_client()
    collection = _collection_name(domain)
    if not client:
        return f"The core principles of {domain} are best explored through trusted domain sources."

    embedder = _embedder()
    if not embedder:
        return f"The core principles of {domain} are best explored through trusted domain sources."

    try:
        vector = embedder.embed_query(query)
    except Exception:
        return f"The core principles of {domain} are best explored through trusted domain sources."

    top_k = int(os.getenv("QDRANT_TOP_K", "5"))
    query_filter = None
    filter_parts: list[Any] = []
    if tenant_id:
        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            filter_parts.append(FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)))
        except Exception:
            pass

    if os.getenv("QDRANT_FILTER_BY_DOMAIN", "").strip().lower() in {"1", "true", "yes", "on"}:
        try:
            from qdrant_client.models import FieldCondition, MatchValue

            key = (os.getenv("QDRANT_DOMAIN_PAYLOAD_KEY") or "domain").strip() or "domain"
            filter_parts.append(FieldCondition(key=key, match=MatchValue(value=domain)))
        except Exception:
            pass

    if filter_parts:
        try:
            from qdrant_client.models import Filter

            query_filter = Filter(must=filter_parts)
        except Exception:
            query_filter = None

    try:
        hits = client.search(
            collection_name=collection,
            query_vector=vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )
    except Exception:
        return f"The core principles of {domain} are best explored through trusted domain sources."

    if not hits:
        return "No matching passages were found in the knowledge base for this query."

    parts: list[str] = []
    for i, h in enumerate(hits, start=1):
        payload: dict[str, Any] = h.payload or {}
        text = str(
            payload.get("text") or payload.get("chunk_text") or payload.get("content") or ""
        ).strip()
        if text:
            parts.append(f"[{i}] {text}")
    if not parts:
        return "Retrieved points had no text payload fields (text/chunk_text/content)."
    return "\n\n".join(parts)
