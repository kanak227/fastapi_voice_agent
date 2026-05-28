from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx
from starlette.requests import Request

from app.core.domain_map import resolve_chat_url
from app.services.runtime_clients import runtime_clients

logger = logging.getLogger(__name__)

# Cap upstream error bodies to avoid loading huge payloads into memory
_MAX_UPSTREAM_ERROR_BYTES = int(os.getenv("GATEWAY_UPSTREAM_ERROR_BODY_MAX_BYTES", "16384"))


def structured_upstream_detail(body_text: str) -> dict[str, Any]:
    """
    Normalize bot error body for HTTPException.detail: JSON object passthrough, else stable wrapper
    so clients can use detail['message'] (and detail['type'] == 'upstream_error').
    """
    raw = (body_text or "").strip()
    if not raw:
        return {"message": "", "type": "upstream_error"}
    try:
        parsed: Any = json.loads(raw)
    except json.JSONDecodeError:
        return {"message": body_text, "type": "upstream_error"}
    if isinstance(parsed, dict):
        return parsed
    return {"message": raw, "type": "upstream_error", "parsed": parsed}


class UpstreamBotHttpError(Exception):
    """Domain bot returned a non-success HTTP status; carries status and structured detail dict."""

    __slots__ = ("status_code", "detail")

    def __init__(self, status_code: int, detail: dict[str, Any]) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"upstream HTTP {status_code}")


async def _read_body_limited(resp: httpx.Response, max_bytes: int) -> bytes:
    buf = bytearray()
    async for chunk in resp.aiter_bytes():
        if not chunk:
            continue
        remaining = max_bytes - len(buf)
        if remaining <= 0:
            break
        buf.extend(chunk[:remaining])
    return bytes(buf)


async def _get_cloud_run_id_token(audience: str) -> str | None:
    """
    Fetch a Google Cloud identity token for Cloud Run service-to-service auth.
    Only works when running on GCP (Cloud Run, GCE, etc.).
    Returns None when running locally or if the metadata server is unavailable.
    """
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(
                f"http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity",
                params={"audience": audience},
                headers={"Metadata-Flavor": "Google"},
            )
            if resp.status_code == 200:
                return resp.text.strip()
    except Exception:
        pass
    return None


async def open_bot_stream_post(
    *,
    domain_key: str,
    json_body: dict,
    tenant_id: str,
    request_id: str,
    request: Request | None = None,
) -> tuple[str, AsyncIterator[bytes]]:
    """
    POST to the domain bot /chat with Accept: text/event-stream.
    Returns (Content-Type from upstream, async iterator of body chunks).
    The response stream is closed when the iterator finishes or is garbage-collected;
    use the iterator to completion to avoid leaks.

    On HTTP 4xx/5xx, raises :class:`UpstreamBotHttpError` with structured ``detail`` for clients.

    If ``request`` is provided, stops reading the upstream stream when the client disconnects
    so the httpx response is closed and bot work can wind down.
    """
    url = resolve_chat_url(domain_key)
    token = (os.getenv("GATEWAY_TO_BOT_SERVICE_TOKEN") or os.getenv("SERVICE_TOKEN") or "").strip()
    headers: dict[str, str] = {
        "X-Request-ID": request_id,
        "X-Tenant-Id": tenant_id,
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    if token:
        headers["X-Service-Token"] = token

    # On Cloud Run, add Google identity token for service-to-service auth.
    # Skip for loopback URLs — in the merged container the gateway and bots
    # share a process tree and talk over 127.0.0.1, no auth needed.
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    audience = f"{parsed.scheme}://{parsed.netloc}"
    is_loopback = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if not is_loopback:
        id_token = await _get_cloud_run_id_token(audience)
        if id_token:
            headers["Authorization"] = f"Bearer {id_token}"

    if runtime_clients.http is None:
        await runtime_clients.startup()
    client = runtime_clients.get_http()
    req = client.build_request("POST", url, json=json_body, headers=headers)
    logger.info(
        "bot_stream_start request_id=%s tenant_id=%s domain_key=%s url=%s",
        request_id,
        tenant_id,
        domain_key,
        url,
    )
    # httpx>=0.28: timeout is configured on AsyncClient, not on send().
    resp = await client.send(req, stream=True)
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError:
        body_text = ""
        try:
            raw = await _read_body_limited(resp, _MAX_UPSTREAM_ERROR_BYTES)
            body_text = raw.decode("utf-8", errors="replace")
        finally:
            await resp.aclose()
        detail = structured_upstream_detail(body_text)
        preview = body_text[:500] + ("…" if len(body_text) > 500 else "")
        logger.warning(
            "bot_http_error request_id=%s status=%s body_preview=%s",
            request_id,
            resp.status_code,
            preview,
        )
        raise UpstreamBotHttpError(resp.status_code, detail) from None

    media_type = resp.headers.get("content-type") or "text/event-stream"

    async def iter_body() -> AsyncIterator[bytes]:
        try:
            async for chunk in resp.aiter_bytes():
                if request is not None and await request.is_disconnected():
                    logger.info(
                        "client_disconnected_cancel_upstream request_id=%s",
                        request_id,
                    )
                    break
                if chunk:
                    yield chunk
        finally:
            await resp.aclose()

    return media_type, iter_body()
