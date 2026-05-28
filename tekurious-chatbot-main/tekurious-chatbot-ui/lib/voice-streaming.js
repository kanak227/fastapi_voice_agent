import { createParser } from "@/app/api/eventsource-parser.js";
import { getCurrentTtsSettings } from "@/lib/tts-settings.js";

function normalizeVoiceErrorMessage(reason) {
  const text = String(reason || "").trim();
  if (!text) return "Voice streaming turn failed.";
  return text;
}

export async function streamRecordedVoiceTurn({
  audio_b64,
  sample_rate_hz,
  session_id,
  domain,
  language = "en-US",
  history = [],
  onAudioChunk,
  onFinalText,
  onTextToken,
  onTranscript,
  stream = false,
  abortSignal = null,
  tts_provider = null,
  tts_voice = null,
}) {
  // Auto-pick from the global TTS settings singleton if the caller didn't pass them
  // — saves having to thread these through every dashboard component.
  const settings = getCurrentTtsSettings();
  const effectiveProvider = tts_provider || settings.provider || null;
  const effectiveVoice = tts_voice || settings.voiceId || null;

  const response = await fetch("/api/Voice/agent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id,
      audio_b64,
      sample_rate_hz,
      domain,
      language,
      stream,
      history,
      ...(effectiveProvider ? { tts_provider: effectiveProvider } : {}),
      ...(effectiveVoice ? { tts_voice: effectiveVoice } : {}),
    }),
    signal: abortSignal || undefined,
  });

  if (stream && response.headers.get("content-type")?.includes("text/event-stream")) {
    if (!response.ok || !response.body) {
      throw new Error(normalizeVoiceErrorMessage("Voice stream failed."));
    }

    let transcript = "";
    let finalText = "";
    let streamedText = "";
    let guardrailBlocked = false;
    const audioChunks = [];

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let sseBuffer = "";

    function parseSSEBlock(block) {
      let eventName = "message";
      const dataLines = [];
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) eventName = line.slice(6).trim() || eventName;
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
      }
      return { event: eventName, data: dataLines.join("\n") };
    }

    let playChain = Promise.resolve();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        sseBuffer += decoder.decode(value, { stream: true });

        // Process complete SSE blocks (separated by \n\n)
        let sepIdx;
        while ((sepIdx = sseBuffer.indexOf("\n\n")) >= 0) {
          const block = sseBuffer.slice(0, sepIdx).trim();
          sseBuffer = sseBuffer.slice(sepIdx + 2);
          if (!block) continue;

          const ev = parseSSEBlock(block);

          if (ev.event === "input") {
            try {
              const d = JSON.parse(ev.data);
              const t = String(d.transcript || "").trim();
              if (t) { transcript = t; onTranscript?.(t); }
            } catch { /* ignore */ }
            continue;
          }

          if (ev.event === "text") {
            try {
              const raw = JSON.parse(ev.data);
              const part = typeof raw === "string" ? raw : String(raw?.text ?? raw ?? "");
              if (part) { streamedText += part; onTextToken?.(part); }
            } catch {
              const fb = String(ev.data || "");
              if (fb) { streamedText += fb; onTextToken?.(fb); }
            }
            continue;
          }

          if (ev.event === "audio") {
            let d = {};
            try { d = JSON.parse(ev.data); } catch { continue; }
            if (!d?.audio_b64) continue;
            audioChunks.push(d);
            // Queue audio playback — runs concurrently while text keeps streaming.
            // We pre-decode the next chunk's data URL on its own Audio element
            // before the previous one ends, so the browser doesn't pause to
            // parse a fresh blob between consecutive sentences.
            if (onAudioChunk) {
              const decoded = (() => {
                try {
                  const a = new Audio(
                    `data:${d.mime_type || "audio/mpeg"};base64,${d.audio_b64}`
                  );
                  a.preload = "auto";
                  // Force the browser to start fetching/decoding now.
                  a.load();
                  return { ...d, _preloaded: a };
                } catch {
                  return d;
                }
              })();
              playChain = playChain.then(() => onAudioChunk(decoded));
            }
            continue;
          }

          if (ev.event === "final_text") {
            try {
              const raw = JSON.parse(ev.data);
              finalText = typeof raw === "string" ? raw : String(raw?.text ?? raw ?? "").trim();
            } catch { finalText = String(ev.data || "").trim(); }
            if (finalText) onFinalText?.(finalText);
            continue;
          }

          if (ev.event === "done") {
            try {
              const d = JSON.parse(ev.data);
              if (d?.guardrail) guardrailBlocked = true;
            } catch { /* ignore */ }
          }
        }
      }

      // Process any remaining buffer
      if (sseBuffer.trim()) {
        const ev = parseSSEBlock(sseBuffer.trim());
        if (ev.event === "final_text") {
          try {
            const raw = JSON.parse(ev.data);
            finalText = typeof raw === "string" ? raw : String(raw?.text ?? raw ?? "").trim();
          } catch { finalText = String(ev.data || "").trim(); }
          if (finalText) onFinalText?.(finalText);
        }
      }

      if (!finalText) {
        const fallbackText = String(streamedText || "").trim();
        if (fallbackText) { finalText = fallbackText; onFinalText?.(fallbackText); }
      }

      // Wait for all queued audio to finish playing
      await playChain;
    } catch (err) {
      // AbortError is expected when user stops playback
      if (err.name !== "AbortError") throw err;
    } finally {
      reader.releaseLock?.();
    }

    return {
      ok: true,
      transcript,
      final_text: finalText,
      audio_chunks: audioChunks.sort(
        (a, b) => Number(a?.index ?? 0) - Number(b?.index ?? 0)
      ),
      guardrail_blocked: guardrailBlocked,
    };
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(normalizeVoiceErrorMessage(data?.error || data?.detail || "Voice request failed."));
  }

  const finalText = String(data?.final_text || "").trim();
  const transcript = String(data?.transcript || "").trim();
  if (transcript && onTranscript) {
    onTranscript(transcript);
  }
  if (finalText && onFinalText) {
    onFinalText(finalText);
  }

  const chunks = Array.isArray(data?.audio_chunks) ? data.audio_chunks : [];
  chunks.sort((a, b) => Number(a?.index ?? 0) - Number(b?.index ?? 0));

  for (const chunk of chunks) {
    if (chunk?.audio_b64 && onAudioChunk) {
      await onAudioChunk(chunk);
    }
  }

  return {
    ok: true,
    transcript,
    final_text: finalText,
    audio_chunks: chunks,
    guardrail_blocked: Boolean(data?.guardrail_blocked),
  };
}
