"use client";

/**
 * Single source of truth for TTS provider + voice across all dashboards.
 *
 * Persists to localStorage so the user's choice survives reloads.
 * Components subscribe via the `useTtsSettings` hook and any code that
 * actually fires a voice request reads `getCurrentTtsSettings()` so it
 * always sees the latest value (no stale closures).
 */

import { useEffect, useState } from "react";

const STORAGE_KEY = "tekurious.tts.settings.v1";

const DEFAULTS = Object.freeze({
  provider: "elevenlabs", // "elevenlabs" (online) | "qwen" (offline)
  voiceId: "",            // empty = backend default
});

const listeners = new Set();
let current = { ...DEFAULTS };

function readFromStorage() {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object") {
      return {
        provider: parsed.provider === "qwen" ? "qwen" : "elevenlabs",
        voiceId: typeof parsed.voiceId === "string" ? parsed.voiceId : "",
      };
    }
  } catch {
    /* ignore corrupt JSON */
  }
  return null;
}

function writeToStorage(value) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch {
    /* quota / privacy mode */
  }
}

// Hydrate from storage on first import in the browser.
if (typeof window !== "undefined") {
  const stored = readFromStorage();
  if (stored) current = stored;
}

function notify() {
  for (const fn of listeners) {
    try { fn(current); } catch { /* ignore listener errors */ }
  }
}

export function getCurrentTtsSettings() {
  return current;
}

export function setTtsSettings(partial) {
  const next = {
    provider: partial?.provider === "qwen" ? "qwen" : (partial?.provider === "elevenlabs" ? "elevenlabs" : current.provider),
    voiceId: typeof partial?.voiceId === "string" ? partial.voiceId : current.voiceId,
  };
  // If provider switched, clear voiceId so the next selection happens against the right list.
  if (partial?.provider && partial.provider !== current.provider && !("voiceId" in partial)) {
    next.voiceId = "";
  }
  current = next;
  writeToStorage(current);
  notify();
}

export function subscribeTtsSettings(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function useTtsSettings() {
  const [state, setState] = useState(current);
  useEffect(() => {
    setState(current); // sync on mount in case storage hydrated after first render
    return subscribeTtsSettings(setState);
  }, []);
  return state;
}
