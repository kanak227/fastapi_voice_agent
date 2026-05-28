"use client";

/**
 * Floating popover that lets the user pick:
 *   - Online (ElevenLabs cloud) vs Offline (self-hosted Qwen3 + MMS)
 *   - A specific voice from the active provider's catalog
 *
 * Drop one of these into any dashboard. State is stored globally in
 * `lib/tts-settings`, and `voice-streaming.js` reads from there at request
 * time, so the same panel works for every dashboard with no per-page wiring.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { Cloud, CloudOff, Mic, Loader2 } from "lucide-react";
import { setTtsSettings, useTtsSettings } from "@/lib/tts-settings";

function classNames(...parts) {
  return parts.filter(Boolean).join(" ");
}

function VoiceListItem({ voice, isActive, onPick }) {
  const subtitle = [voice.locale, voice.gender]
    .filter((p) => typeof p === "string" && p.trim())
    .join(" \u2022 ");
  return (
    <button
      type="button"
      onClick={() => onPick(voice.voice_id)}
      className={classNames(
        "w-full flex items-center gap-2 px-3 py-2 text-sm text-left rounded-md transition-colors",
        isActive ? "bg-zinc-100 font-medium text-zinc-900" : "text-zinc-700 hover:bg-zinc-50"
      )}
    >
      <Mic className="h-3.5 w-3.5 text-zinc-500" />
      <div className="flex-1 min-w-0">
        <div className="truncate">{voice.name || voice.voice_id}</div>
        {subtitle && (
          <div className="text-[11px] text-zinc-500 truncate">{subtitle}</div>
        )}
      </div>
      {isActive && <span className="text-zinc-400">\u2713</span>}
    </button>
  );
}

export function TtsSettingsPanel({ className = "", language = "" }) {
  const { provider, voiceId } = useTtsSettings();
  const [open, setOpen] = useState(false);
  const [voices, setVoices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const popoverRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const handler = (event) => {
      if (popoverRef.current && !popoverRef.current.contains(event.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  useEffect(() => {
    let abort = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const res = await fetch(
          `/api/Voice/voices?tts_provider=${encodeURIComponent(provider)}${language ? `&language=${encodeURIComponent(language)}` : ""}`
        );
        const data = await res.json().catch(() => ({}));
        if (abort) return;
        const list = Array.isArray(data?.voices) ? data.voices : [];
        setVoices(list);
        if (list.length === 0) setError("No voices available right now.");
      } catch (err) {
        if (!abort) setError("Couldn't load voices.");
      } finally {
        if (!abort) setLoading(false);
      }
    }
    load();
    return () => {
      abort = true;
    };
  }, [provider, language]);

  const activeVoice = useMemo(() => {
    if (!voiceId) return null;
    return voices.find((v) => v.voice_id === voiceId) || null;
  }, [voices, voiceId]);

  const summary = provider === "qwen" ? "Offline" : "Online";
  const Icon = provider === "qwen" ? CloudOff : Cloud;

  return (
    <div className={classNames("relative", className)} ref={popoverRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-zinc-200 bg-white hover:bg-zinc-50 text-xs text-zinc-700 transition-colors"
        title="Voice provider settings"
      >
        <Icon className="h-3.5 w-3.5 text-zinc-500" />
        <span>{summary}</span>
        {activeVoice && (
          <>
            <span className="text-zinc-300">\u00b7</span>
            <span className="max-w-[7rem] truncate">
              {activeVoice.name || activeVoice.voice_id}
            </span>
          </>
        )}
        <span className="text-zinc-400">\u25be</span>
      </button>

      {open && (
        <div className="absolute bottom-full right-0 mb-1 z-50 w-72 rounded-xl border border-zinc-200 bg-white shadow-lg overflow-hidden">
          <div className="px-3 py-2 border-b border-zinc-100">
            <div className="text-[11px] uppercase tracking-wide text-zinc-500 mb-1.5">
              Voice provider
            </div>
            <div className="grid grid-cols-2 gap-1 p-0.5 bg-zinc-100 rounded-lg">
              <button
                type="button"
                onClick={() => setTtsSettings({ provider: "elevenlabs" })}
                className={classNames(
                  "flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-xs font-medium transition-colors",
                  provider === "elevenlabs"
                    ? "bg-white shadow-sm text-zinc-900"
                    : "text-zinc-600 hover:text-zinc-900"
                )}
              >
                <Cloud className="h-3.5 w-3.5" />
                Online
              </button>
              <button
                type="button"
                onClick={() => setTtsSettings({ provider: "qwen" })}
                className={classNames(
                  "flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-xs font-medium transition-colors",
                  provider === "qwen"
                    ? "bg-white shadow-sm text-zinc-900"
                    : "text-zinc-600 hover:text-zinc-900"
                )}
              >
                <CloudOff className="h-3.5 w-3.5" />
                Offline
              </button>
            </div>
            <div className="text-[11px] text-zinc-500 mt-1.5">
              {provider === "qwen"
                ? "Self-hosted Qwen3 + MMS, runs on our GPU."
                : "ElevenLabs cloud \u2014 needs internet."}
            </div>
          </div>

          <div className="px-3 py-2">
            <div className="flex items-center justify-between mb-1.5">
              <div className="text-[11px] uppercase tracking-wide text-zinc-500">
                Voice
              </div>
              {loading && (
                <Loader2 className="h-3 w-3 animate-spin text-zinc-400" />
              )}
            </div>
            <div className="max-h-56 overflow-y-auto -mx-1 px-1">
              <VoiceListItem
                voice={{ voice_id: "", name: "Default", locale: "auto" }}
                isActive={!voiceId}
                onPick={() => setTtsSettings({ voiceId: "" })}
              />
              {voices.map((v) => (
                <VoiceListItem
                  key={v.voice_id || v.name}
                  voice={v}
                  isActive={voiceId === v.voice_id}
                  onPick={(id) => setTtsSettings({ voiceId: id })}
                />
              ))}
              {!loading && voices.length === 0 && (
                <div className="text-[11px] text-zinc-500 px-2 py-3 text-center">
                  {error || "No voices available."}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default TtsSettingsPanel;
