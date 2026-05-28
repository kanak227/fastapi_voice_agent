"""Domain slug -> domain bot /chat URL. Configure via DOMAIN_MAP_JSON (12-factor); fallback for local Docker Compose."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Final

from dotenv import dotenv_values

logger = logging.getLogger(__name__)

# Default: full URL including /chat path (Docker Compose service names).
_DEFAULT_DOMAIN_MAP: Final[dict[str, str]] = {
    "religious": "http://bot-religious:8000/chat",
    "education": "http://bot-education:8000/chat",
    "digital-literacy": "http://bot-digital-literacy:8000/chat",
    "design-thinking": "http://bot-design-thinking:8000/chat",
    "wellbeing": "http://bot-wellbeing:8000/chat",
    "sustainability": "http://bot-sustainability:8000/chat",
    "global-citizenship": "http://bot-global-citizenship:8000/chat",
    "entrepreneurship": "http://bot-entrepreneurship:8000/chat",
    "emotional-intelligence": "http://bot-emotional-intelligence:8000/chat",
    "financial-literacy": "http://bot-financial-literacy:8000/chat",
}


def _domain_map_json_raw() -> str:
    """Resolve DOMAIN_MAP_JSON in this order:

    1) Explicit ``os.environ`` value (set by the merged container or by ops)
    2) ``fastapi_server/.env`` for local development convenience

    The explicit env var wins over the .env file so production deploys
    can never accidentally pick up a developer's local override.
    """
    from_env = (os.getenv("DOMAIN_MAP_JSON") or "").strip()
    if from_env:
        return from_env
    env_file = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_file.is_file():
        vals = dotenv_values(env_file)
        from_file = (vals.get("DOMAIN_MAP_JSON") or "").strip()
        if from_file:
            return from_file
    return ""


def _load_domain_map() -> dict[str, str]:
    raw = _domain_map_json_raw()
    if not raw:
        return dict(_DEFAULT_DOMAIN_MAP)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning(
            "DOMAIN_MAP_JSON is not valid JSON (%s). Using default routing map.",
            exc,
        )
        return dict(_DEFAULT_DOMAIN_MAP)
    if not isinstance(data, dict):
        logger.warning(
            "DOMAIN_MAP_JSON must be a JSON object mapping slug -> url. Using default routing map."
        )
        return dict(_DEFAULT_DOMAIN_MAP)
    # Merge on top of defaults so local dev can override e.g. only `wellbeing` → 127.0.0.1
    # without duplicating every slug; Docker Compose can still use an empty env for full defaults.
    out: dict[str, str] = dict(_DEFAULT_DOMAIN_MAP)
    overrides = 0
    override_slugs: list[str] = []
    for key, value in data.items():
        if not isinstance(key, str) or not isinstance(value, str):
            logger.warning("Skipping invalid DOMAIN_MAP_JSON entry: %r -> %r", key, value)
            continue
        ks, vs = key.strip(), value.strip()
        if ks and vs:
            out[ks] = vs
            overrides += 1
            override_slugs.append(ks)
        else:
            logger.warning("Skipping empty DOMAIN_MAP_JSON entry: %r -> %r", key, value)
    if overrides == 0:
        logger.warning(
            "DOMAIN_MAP_JSON produced no valid slug->url entries. Using default routing map."
        )
        return dict(_DEFAULT_DOMAIN_MAP)
    if overrides <= 3:
        logger.warning(
            "DOMAIN_MAP_JSON overrides only %s slug(s) %s; others keep Docker default URLs. "
            "If you see 502 locally, fix ports (wellbeing is 8105) and check for a stale "
            "DOMAIN_MAP_JSON in your shell or Windows user env — it overrides fastapi_server/.env.",
            overrides,
            override_slugs,
        )
    return out


DOMAIN_MAP: dict[str, str] = _load_domain_map()


def domain_slugs() -> frozenset[str]:
    """Slugs present in the active DOMAIN_MAP (env or default)."""
    return frozenset(DOMAIN_MAP.keys())


def resolve_chat_url(domain_key: str) -> str:
    url = DOMAIN_MAP.get(domain_key)
    if not url:
        raise KeyError(f"No DOMAIN_MAP entry for domain_key={domain_key!r}")
    return url
