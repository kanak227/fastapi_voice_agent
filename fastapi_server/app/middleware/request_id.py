from __future__ import annotations

import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("uvicorn.error")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Ensure every request has X-Request-ID (accept client header or generate UUID)."""

    async def dispatch(self, request: Request, call_next):
        rid = (request.headers.get("x-request-id") or "").strip() or str(uuid.uuid4())
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response
