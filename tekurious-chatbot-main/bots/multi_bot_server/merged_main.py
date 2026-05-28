"""Unified gateway + multi-bot server.

This is the single Cloud Run entrypoint that combines:
  1) The FastAPI gateway (was a separate service) — `app.main:create_app()`
  2) The 10 domain-bot subprocesses (was the multi-bot proxy) — started in startup
  3) An in-process proxy route `/bot/{slug}/{path}` so `bot_gateway_client`
     can reach each bot via `http://127.0.0.1:8001-8010` with zero network hops.

Why merge: each Cloud Run service with min-instances=1 burns ~$13/mo for the
idle baseline. Running gateway + bots in one container drops that cost while
also removing service-to-service auth + an extra network hop on every chat.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse

# Tell the gateway where to find each bot BEFORE its config module loads.
# All bots run as subprocesses on 127.0.0.1:8001..8010 (see BOT_CONFIG below).
# We use plain assignment (not setdefault) to override any leftover
# DOMAIN_MAP_JSON the operator might have set elsewhere — in the merged
# container the loopback ports below are the only correct values.
_DEFAULT_LOCAL_DOMAIN_MAP = (
    '{"religious":"http://127.0.0.1:8001/chat",'
    '"education":"http://127.0.0.1:8002/chat",'
    '"digital-literacy":"http://127.0.0.1:8003/chat",'
    '"design-thinking":"http://127.0.0.1:8004/chat",'
    '"wellbeing":"http://127.0.0.1:8005/chat",'
    '"sustainability":"http://127.0.0.1:8006/chat",'
    '"global-citizenship":"http://127.0.0.1:8007/chat",'
    '"entrepreneurship":"http://127.0.0.1:8008/chat",'
    '"emotional-intelligence":"http://127.0.0.1:8009/chat",'
    '"financial-literacy":"http://127.0.0.1:8010/chat"}'
)
os.environ["DOMAIN_MAP_JSON"] = _DEFAULT_LOCAL_DOMAIN_MAP

# Now that DOMAIN_MAP_JSON is set, import the gateway app.
# The gateway's app/ directory is copied into /app/gateway_app in the Docker image,
# and we add /app to sys.path so `import app.main` resolves to the gateway code.
from app.main import app as gateway_app  # noqa: E402  (import-after-side-effect by design)

app = gateway_app

# ---------------------------------------------------------------------------
# Bot subprocess management
# ---------------------------------------------------------------------------
# In the production container, merged_main.py lives at /app and bots are
# at /app/<slug>-ai/src. Locally during dev (`python multi_bot_server/merged_main.py`)
# the file lives at <repo>/tekurious-chatbot-main/bots/multi_bot_server/merged_main.py
# and the bots are siblings of multi_bot_server/, so parent.parent is right.
# We pick the layout that exists.
_HERE = Path(__file__).resolve().parent
if (_HERE / "religious-ai" / "src").is_dir():
    BOTS_ROOT = _HERE                       # production: /app
else:
    BOTS_ROOT = _HERE.parent                # dev: <repo>/tekurious-chatbot-main/bots

BOT_CONFIG = [
    ("religious",              "religious-ai",              8001),
    ("education",              "education-ai",              8002),
    ("digital-literacy",       "digital-literacy-ai",       8003),
    ("design-thinking",        "design-thinking-ai",        8004),
    ("wellbeing",              "wellbeing-ai",              8005),
    ("sustainability",         "sustainability-ai",         8006),
    ("global-citizenship",     "global-citizenship-ai",     8007),
    ("entrepreneurship",       "entrepreneurship-ai",       8008),
    ("emotional-intelligence", "emotional-intelligence-ai", 8009),
    ("financial-literacy",     "financial-literacy-ai",     8010),
]

_bot_ports: dict[str, int] = {}
_processes: list[subprocess.Popen] = []


def _start_bot(slug: str, bot_dir: str, port: int) -> subprocess.Popen:
    src_path = str(BOTS_ROOT / bot_dir / "src")
    env = {**os.environ, "PORT": str(port), "UVICORN_RELOAD": "0"}
    # CRITICAL: do NOT use subprocess.PIPE — the pipe buffer fills up and blocks
    # the bot subprocess as soon as it produces ~64KB of log output. Inherit
    # parent's stdout/stderr so Cloud Run captures it.
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.main:app",
         "--host", "127.0.0.1", "--port", str(port), "--workers", "1"],
        cwd=src_path,
        env=env,
        stdout=None,
        stderr=None,
    )


def _wait_for_bot(port: int, timeout: float = 60.0) -> bool:
    """Poll until the bot's /health endpoint responds."""
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


@app.on_event("startup")
async def _start_bot_subprocesses() -> None:
    print("[merged] Starting domain bot subprocesses...", flush=True)
    for slug, bot_dir, port in BOT_CONFIG:
        try:
            proc = _start_bot(slug, bot_dir, port)
            _processes.append(proc)
            _bot_ports[slug] = port
            print(f"[merged]   started {slug} on port {port} (pid={proc.pid})", flush=True)
        except Exception as exc:
            print(f"[merged]   FAILED to start {slug}: {exc}", flush=True)

    # Wait for all bots to come up in parallel.
    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(None, _wait_for_bot, port, 60.0)
        for slug, _, port in BOT_CONFIG if slug in _bot_ports
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    ready = sum(1 for r in results if r is True)
    print(f"[merged] {ready}/{len(BOT_CONFIG)} bots ready", flush=True)


@app.on_event("shutdown")
async def _stop_bot_subprocesses() -> None:
    for proc in _processes:
        try:
            proc.terminate()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# In-process proxy: gateway -> bot subprocess
# ---------------------------------------------------------------------------
# `bot_gateway_client.py` POSTs to URLs from DOMAIN_MAP_JSON. We mapped those
# to http://127.0.0.1:80NN/chat above, which is each bot's native /chat route.
# So we DON'T need a /bot/{slug}/chat proxy here in the merged setup —
# the gateway connects to each bot directly.
#
# However we still expose a /bot/{slug}/{path} compat route for diagnostic
# purposes (debug dashboards, /docs probe scripts) and to keep the API
# surface identical to the old multi-bot-server image so external clients
# that hit it directly still work during the rollout.
# ---------------------------------------------------------------------------
@app.get("/debug/bots")
async def debug_bots() -> dict:
    """Quick liveness probe of every bot subprocess."""
    out: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for slug, port in _bot_ports.items():
            try:
                r = await client.get(f"http://127.0.0.1:{port}/health")
                out[slug] = {"port": port, "status": r.status_code, "body": r.text[:120]}
            except Exception as exc:
                out[slug] = {"port": port, "error": str(exc)}
    return out


@app.api_route(
    "/bot/{slug}/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    include_in_schema=False,
)
async def proxy_bot_compat(slug: str, path: str, request: Request):
    port = _bot_ports.get(slug)
    if port is None:
        return JSONResponse({"error": f"Bot '{slug}' not found"}, status_code=404)

    target_url = f"http://127.0.0.1:{port}/{path}"
    body = await request.body()
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }

    client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=10.0, read=300.0, write=60.0, pool=10.0)
    )
    try:
        resp = await client.send(
            client.build_request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=dict(request.query_params),
            ),
            stream=True,
        )
    except httpx.RequestError as exc:
        await client.aclose()
        return JSONResponse({"error": f"Bot {slug} unreachable: {exc}"}, status_code=502)

    resp_headers = {
        k: v for k, v in resp.headers.items()
        if k.lower() not in ("content-length", "transfer-encoding")
    }
    content_type = resp_headers.get("content-type", "application/json")

    async def stream_and_close():
        try:
            async for chunk in resp.aiter_bytes():
                yield chunk
        finally:
            await resp.aclose()
            await client.aclose()

    return StreamingResponse(
        stream_and_close(),
        status_code=resp.status_code,
        headers=resp_headers,
        media_type=content_type,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("merged_main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8080")), reload=False)
