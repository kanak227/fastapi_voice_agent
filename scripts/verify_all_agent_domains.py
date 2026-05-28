"""Call unified FastAPI POST /agent/stream once per domain; print SSE summary."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid

import requests

HDRS_DEFAULT = {"Content-Type": "application/json", "X-Tenant-Id": "tenant-demo"}

TESTS: list[tuple[str, str]] = [
    ("religious", "In one sentence, who is Krishna in Indian traditions?"),
    ("education", "In one sentence, what is photosynthesis for Class 10?"),
    ("digital-literacy", "Give one tip for staying safe on the internet."),
    ("design-thinking", "In one sentence, what does empathy mean in design thinking?"),
    ("wellbeing", "Give one practical idea to feel calmer before a test."),
    ("sustainability", "Briefly: why recycle plastic bottles?"),
    ("global-citizenship", "In simple words, what is global citizenship?"),
    ("entrepreneurship", "In one sentence, what is an entrepreneur?"),
    ("emotional-intelligence", "In one sentence, what is emotional intelligence?"),
    ("financial-literacy", "Briefly for kids: what does saving money mean?"),
]


def _normalize_base(raw: str) -> str:
    s = (raw or "").strip().rstrip("/")
    if s.lower().endswith("/agent/stream"):
        s = s[: -len("/agent/stream")].rstrip("/")
    return s or "http://127.0.0.1:8000"


def probe_backend(base: str, headers: dict[str, str]) -> None:
    """Warn if server does not advertise all 10 agent domains."""
    hints: list[str] = []

    # Prefer `/agent/domains` (next to `/agent/stream`), then `/health/agent-domains`.
    check_paths = ["/agent/domains", "/health/agent-domains"]
    got_domains: dict | None = None
    for path in check_paths:
        url = f"{base}{path}"
        try:
            r = requests.get(url, headers={"X-Tenant-Id": headers.get("X-Tenant-Id", "tenant-demo")}, timeout=8)
        except requests.RequestException as e:
            hints.append(f"Could not reach {url}: {e}")
            continue
        if r.status_code != 200:
            hints.append(f"GET {path} -> HTTP {r.status_code} (restart uvicorn from `fastapi_server` if 404)")
            continue
        try:
            got_domains = r.json() or {}
        except requests.JSONDecodeError:
            hints.append(f"{path}: response is not JSON (body may be HTML from a proxy or wrong server).")
            continue
        if not got_domains.get("domains"):
            hints.append(
                f"{path}: JSON missing non-empty `domains` key — try `{base}/health/agent-domains.json` or view raw response."
            )
        break

    if isinstance(got_domains, dict):
        domains = set(got_domains.get("domains") or [])
        cnt = got_domains.get("count")
        if domains and cnt != len(domains):
            hints.append("`count` disagrees with `domains` length; check deployed code.")
        missing = [d for d, _ in TESTS if d not in domains]
        if missing or len(domains) < len(TESTS):
            hints.append(
                f"Expected {len(TESTS)} domains; backend reported {sorted(domains)} missing={missing}"
            )

    # Fallback: peek OpenAPI (older servers expose inline two-value literal on `domain`).
    try:
        o = requests.get(f"{base}/openapi.json", timeout=12)
        if o.status_code == 200:
            spec = o.json()
            agent_dom = (
                ((spec.get("components") or {}).get("schemas") or {}).get("AgentDomain") or {}
            )
            enum_vals = agent_dom.get("enum")
            props = (((spec.get("components") or {}).get("schemas") or {}).get("AgentStreamRequest") or {}).get("properties") or {}
            dom_any = (((props.get("domain") or {}).get("anyOf") or [{}])[0] or {}).get("enum")

            known = []
            if isinstance(enum_vals, list):
                known = enum_vals
            elif isinstance(dom_any, list):
                known = dom_any

            if isinstance(known, list) and len(known) == 2 and set(known) <= {"religious", "education"}:
                hints.append(
                    "OpenAPI still restricts `domain` to religious/education only. "
                    "The process on this port did not reload `app/schemas/agent.py` "
                    "(AgentDomain / StrEnum); stop uvicorn entirely and start again from `fastapi_server`."
                )
    except requests.RequestException:
        pass

    if hints:
        print("--- Backend probe ---")
        for h in hints:
            print(h)
        print("---")


def sse_summarize(resp: requests.Response) -> tuple[str, object]:
    texts: list[str] = []
    final_parts: list[str] = []
    done_payload = None
    cur_event: str | None = None

    for line in resp.iter_lines(decode_unicode=True):
        if line is None:
            continue
        if line.startswith("event:"):
            cur_event = line[6:].strip()
            continue
        if not line.startswith("data:"):
            continue
        payload = line[5:].lstrip()

        ev = cur_event
        cur_event = None

        if ev == "done":
            try:
                done_payload = json.loads(payload)
            except json.JSONDecodeError:
                done_payload = {"raw": payload}
            continue

        if ev not in ("text", "final_text"):
            continue

        try:
            d = json.loads(payload)
            if isinstance(d, str):
                chunk = d
            elif isinstance(d, dict):
                chunk = str(d.get("text") or d.get("content") or d.get("delta") or "")
            else:
                chunk = str(d)
        except json.JSONDecodeError:
            chunk = payload

        if not chunk.strip():
            continue
        if ev == "final_text":
            final_parts.append(chunk)
        else:
            texts.append(chunk)

    merged = "".join(texts).strip()
    finals = "".join(final_parts).strip()
    reply = (finals or merged).strip()
    return reply, done_payload


def main() -> int:
    parser = argparse.ArgumentParser(description="POST /agent/stream for each unified domain.")
    parser.add_argument(
        "--base-url",
        default=os.getenv(
            "AGENT_VERIFY_BASE",
            os.getenv("TEKURIOUS_FASTAPI_URL", "http://127.0.0.1:8000"),
        ).strip(),
        help="Unified FastAPI origin (no /agent/stream). Env: AGENT_VERIFY_BASE or TEKURIOUS_FASTAPI_URL.",
    )
    parser.add_argument(
        "--tenant",
        default=os.getenv("FASTAPI_TENANT_ID", "tenant-demo").strip(),
        help="X-Tenant-Id header.",
    )
    args = parser.parse_args()

    base = _normalize_base(args.base_url)
    stream_url = f"{base}/agent/stream"
    hdrs = {**HDRS_DEFAULT, "X-Tenant-Id": args.tenant}

    print(f"Using backend: {stream_url}")
    probe_backend(base, hdrs)

    failures = 0
    for domain, q in TESTS:
        body = {
            "session_id": str(uuid.uuid4()),
            "input_type": "text",
            "text": q,
            "domain": domain,
            "language": "en-US",
            "use_knowledge": True,
            "output_audio": False,
        }

        print(f"\n=== {domain} ===")
        try:
            r = requests.post(stream_url, headers=hdrs, json=body, stream=True, timeout=180)
            if r.status_code != 200:
                snippet = (r.text or "")[:500]
                print(f"HTTP {r.status_code}: {snippet}")
                if (
                    r.status_code == 422
                    and "religious" in snippet.lower()
                    and "education" in snippet.lower()
                ):
                    print(
                        ">>> Fix: stop all uvicorn processes, then from `fastapi_server` run:\n"
                        ">>>   python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
                    )
                failures += 1
                continue

            reply, done = sse_summarize(r)
            preview = reply[:460] + ("..." if len(reply) > 460 else "")
            print("reply_preview:", preview or "(empty)")
            print("done:", done)

            err_flag = isinstance(done, dict) and isinstance(done.get("error"), str)
            llm_failed = isinstance(done, dict) and done.get("ok") is False and err_flag

            if llm_failed or not preview.strip():
                failures += 1
        except Exception as exc:
            print("EXCEPTION:", type(exc).__name__, exc)
            failures += 1

    print(f"\nFailures: {failures} / {len(TESTS)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
