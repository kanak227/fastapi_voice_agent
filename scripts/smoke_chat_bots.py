#!/usr/bin/env python3
"""
Hit standalone bot services: GET /health and POST /chat with a test query.

Update DEFAULT_MANIFEST ports to match how you run each bot (PORT env).
Or pass --url repeatedly:  --url digital-literacy-ai=http://127.0.0.1:8011

Requires only stdlib. LLM calls need valid .env on each running service.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Iterable

# Adjust ports for your machine. Defaults follow README hints (religious 8000, education 8002)
# and sequential ports for other clones so they can run together.
DEFAULT_MANIFEST: list[tuple[str, str]] = [
    ("religious-ai",              "http://127.0.0.1:8080/bot/religious"),
    ("education-ai",              "http://127.0.0.1:8080/bot/education"),
    ("digital-literacy-ai",       "http://127.0.0.1:8080/bot/digital-literacy"),
    ("design-thinking-ai",        "http://127.0.0.1:8080/bot/design-thinking"),
    ("wellbeing-ai",              "http://127.0.0.1:8080/bot/wellbeing"),
    ("sustainability-ai",         "http://127.0.0.1:8080/bot/sustainability"),
    ("global-citizenship-ai",     "http://127.0.0.1:8080/bot/global-citizenship"),
    ("entrepreneurship-ai",       "http://127.0.0.1:8080/bot/entrepreneurship"),
    ("emotional-intelligence-ai", "http://127.0.0.1:8080/bot/emotional-intelligence"),
    ("financial-literacy-ai",     "http://127.0.0.1:8080/bot/financial-literacy"),
]


def _get(url: str, timeout: float) -> tuple[int, str]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def _post_json(url: str, payload: dict, timeout: float) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def _parse_env_manifest() -> list[tuple[str, str]] | None:
    raw = os.environ.get("BOT_SMOKE_MANIFEST", "").strip()
    if not raw:
        return None
    out: list[tuple[str, str]] = []
    for part in raw.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            continue
        name, base = part.split("=", 1)
        out.append((name.strip(), base.strip().rstrip("/")))
    return out or None


def run(
    manifest: Iterable[tuple[str, str]],
    query: str,
    timeout: float,
    health_only: bool,
) -> int:
    failures = 0
    for name, base in manifest:
        base = base.rstrip("/")
        print(f"\n=== {name} ({base}) ===")
        try:
            st, body = _get(f"{base}/health", timeout)
            print(f"  GET /health -> {st}: {body[:200]}")
            if health_only:
                continue
            stc, chat_body = _post_json(f"{base}/chat", {"query": query}, timeout)
            preview = chat_body[:500] + ("..." if len(chat_body) > 500 else "")
            print(f"  POST /chat -> {stc}: {preview}")
            if stc >= 400:
                failures += 1
            else:
                try:
                    j = json.loads(chat_body)
                    if j.get("status") == "error":
                        failures += 1
                except json.JSONDecodeError:
                    pass
        except urllib.error.HTTPError as e:
            failures += 1
            print(f"  HTTPError {e.code}: {e.read().decode(errors='replace')[:400]}")
        except urllib.error.URLError as e:
            print(f"  SKIP (no server?): {e.reason}")
        except Exception as e:
            failures += 1
            print(f"  FAIL: {e}")

    print(f"\nDone. Failures (HTTP/post error): {failures}")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Smoke-test standalone bots /health and /chat")
    p.add_argument(
        "--query",
        default="Hi - what topics can you help me with?",
        help="Prompt sent as JSON {\"query\": ...}",
    )
    p.add_argument("--timeout", type=float, default=120.0, help="Per-request timeout (LLM may be slow)")
    p.add_argument("--health-only", action="store_true")
    p.add_argument(
        "--url",
        action="append",
        metavar="slug=BASE",
        dest="urls",
        help="Override/add one bot base URL (repeatable), e.g. religious-ai=http://127.0.0.1:8000",
    )
    args = p.parse_args(argv)

    manifest: dict[str, str] = {slug: base for slug, base in DEFAULT_MANIFEST}
    env_m = _parse_env_manifest()
    if env_m:
        for slug, base in env_m:
            manifest[slug] = base
    if args.urls:
        for item in args.urls:
            if "=" not in item:
                print(f"Ignoring bad --url: {item}", file=sys.stderr)
                continue
            k, v = item.split("=", 1)
            manifest[k.strip()] = v.strip().rstrip("/")

    ordered_keys = [
        slug for slug, _ in DEFAULT_MANIFEST if slug in manifest
    ]
    extras = sorted(set(manifest) - set(ordered_keys))
    final = [(k, manifest[k]) for k in ordered_keys + extras]

    return run(final, args.query.strip(), args.timeout, args.health_only)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
