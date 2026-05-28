/**
 * Single FastAPI backend (agent stream, /voice/*, /documents/*).
 * TEKURIOUS_AI_BASE_URL / EDUTHUM_BASE_URL are checked before FASTAPI_VOICE_BASE_URL
 * so one server on 8010 works even if legacy FASTAPI_* vars still point at 8001.
 */
const DEFAULT_FASTAPI_BASE = "http://127.0.0.1:8010";

/** Domains the oldest FastAPI builds accept in JSON `domain`; others must omit it on the wire. */
export const LEGACY_BODY_AGENT_DOMAINS = new Set(["religious", "education"]);

/**
 * Suffix appended to FASTAPI_TENANT_ID so `resolve_agent_domain` derives the slug from tenant_id
 * (must match substring rules in `fastapi_server/app/core/intent_guard.py`).
 */
export const SMART_DOMAIN_TENANT_SUFFIX = Object.freeze({
  "digital-literacy": "digital",
  "design-thinking": "design",
  wellbeing: "wellbeing",
  sustainability: "sustainability",
  "global-citizenship": "global",
  entrepreneurship: "entrepreneur",
  "emotional-intelligence": "emotional",
  "financial-literacy": "financial",
});

export const KNOWN_CHAT_AGENT_DOMAIN_SLUGS = new Set([
  ...LEGACY_BODY_AGENT_DOMAINS,
  ...Object.keys(SMART_DOMAIN_TENANT_SUFFIX),
]);

/** @typedef { keyof typeof SMART_DOMAIN_TENANT_SUFFIX | "religious" | "education"} AgentDomainSlug */

/** @returns {boolean} */
export function shouldAttachDomainBodyField(canonicalSlug) {
  return LEGACY_BODY_AGENT_DOMAINS.has(String(canonicalSlug || "").trim().toLowerCase());
}

/**
 * Tenant id embedding domain hints for SmartE bots (when body.domain must be omitted for old backends).
 * @param {string} canonicalSlug
 */
export function getFastApiTenantIdForAgentDomain(canonicalSlug) {
  const slug = String(canonicalSlug || "").trim().toLowerCase();
  const baseRaw = getFastApiTenantId();
  if (LEGACY_BODY_AGENT_DOMAINS.has(slug)) return baseRaw;

  const suf = SMART_DOMAIN_TENANT_SUFFIX[slug];
  if (!suf) return baseRaw;

  const combined = `${baseRaw}-${suf}`;
  if (combined.length <= 64) return combined;

  const maxBase = 64 - suf.length - 1;
  const trimmedBase =
    baseRaw.length > maxBase ? baseRaw.slice(0, Math.max(12, maxBase)) : baseRaw;
  return `${trimmedBase}-${suf}`.slice(0, 64);
}

/** Build `{ domain?: string }` for POST /agent/stream (omit field when old backend rejects it). */
export function attachAgentDomainPayloadField(payload, canonicalSlug) {
  const slug = String(canonicalSlug || "").trim().toLowerCase();
  const out = { ...payload };
  if (shouldAttachDomainBodyField(slug)) {
    out.domain = slug;
  } else if ("domain" in out) {
    delete out.domain;
  }
  return out;
}

export function getFastApiBaseUrl() {
  const raw =
    process.env.TEKURIOUS_FASTAPI_URL ||
    process.env.TEKURIOUS_AI_BASE_URL ||
    process.env.EDUTHUM_BASE_URL ||
    process.env.FASTAPI_BASE_URL ||
    process.env.FASTAPI_VOICE_BASE_URL ||
    DEFAULT_FASTAPI_BASE;
  return String(raw).trim().replace(/\/+$/, "");
}

export function getFastApiTenantId() {
  return String(process.env.FASTAPI_TENANT_ID || "tenant-demo").trim();
}
