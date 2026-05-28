from __future__ import annotations

"""Resolve which domain bot to call from explicit client domain and tenant id (no LLM, no regex on user text)."""

from app.core.domain_map import domain_slugs


def resolve_agent_domain_for_routing(
    tenant_id: str | None,
    explicit_domain: str | None,
) -> str | None:
    """
    Pick a domain routing key that must exist in ``DOMAIN_MAP`` / ``DOMAIN_MAP_JSON``.

    Routing URLs are loaded in ``app.core.domain_map`` from the environment variable
    ``DOMAIN_MAP_JSON`` when set; otherwise the built-in Docker Compose defaults apply.

    Priority:
    1) Explicit ``domain`` from the client (must be a slug present in the active map).
    2) Substring heuristics on ``X-Tenant-Id`` (stable product mapping, not message content).
    """
    allowed = domain_slugs()
    d = (explicit_domain or "").strip().lower()
    if d in allowed:
        return d

    t = (tenant_id or "").lower()
    tenant_rules = (
        ("religious", "religious"),
        ("darshan", "religious"),
        ("spiritual", "religious"),
        ("eduthum", "education"),
        ("education", "education"),
        ("digital", "digital-literacy"),
        ("literacy", "digital-literacy"),
        ("design", "design-thinking"),
        ("wellbeing", "wellbeing"),
        ("well-being", "wellbeing"),
        ("sustainability", "sustainability"),
        ("global", "global-citizenship"),
        ("citizenship", "global-citizenship"),
        ("entrepreneur", "entrepreneurship"),
        ("startup", "entrepreneurship"),
        ("emotional", "emotional-intelligence"),
        ("eq", "emotional-intelligence"),
        ("financial", "financial-literacy"),
        ("finance", "financial-literacy"),
        ("tekurious", "education"),
        ("cbse", "education"),
        ("school", "education"),
        ("class10", "education"),
        ("class9", "education"),
        ("class12", "education"),
        ("class11", "education"),
        ("edu", "education"),
    )
    for needle, dom in tenant_rules:
        if needle in t and dom in allowed:
            return dom
    return None
