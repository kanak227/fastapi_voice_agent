from __future__ import annotations

import httpx

try:
    import redis.asyncio as redis
except Exception:  # pragma: no cover - optional dependency
    redis = None

from app.core import config


class RuntimeClients:
    """Shared async clients for the thin gateway (HTTP to bots; optional Redis cache)."""

    def __init__(self) -> None:
        self.http: httpx.AsyncClient | None = None
        self.redis: object | None = None

    async def startup(self) -> None:
        if self.http is None:
            # Long read for domain-bot SSE / streaming LLM (send() cannot pass per-call timeout in httpx 0.28+).
            read_s = max(float(config.HTTP_CLIENT_TIMEOUT_SECONDS), 120.0)
            self.http = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=30.0, read=read_s, write=60.0, pool=30.0)
            )
        if self.redis is None and redis is not None and config.REDIS_URL:
            try:
                self.redis = redis.from_url(config.REDIS_URL, decode_responses=True)
                await self.redis.ping()
            except Exception:
                self.redis = None

    async def shutdown(self) -> None:
        if self.http is not None:
            await self.http.aclose()
            self.http = None
        if self.redis is not None:
            await self.redis.close()
            self.redis = None

    def get_http(self) -> httpx.AsyncClient:
        if self.http is None:
            raise RuntimeError("Runtime HTTP client is not initialized")
        return self.http

    def get_redis(self) -> object | None:
        return self.redis


runtime_clients = RuntimeClients()
