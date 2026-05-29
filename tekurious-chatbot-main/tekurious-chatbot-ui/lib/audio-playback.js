/**
 * Shared audio chunk player for the voice pipeline.
 *
 * The realtime backend streams many small (~1s) WAV windows. Playing each one
 * through a separate HTMLAudioElement leaves an audible gap at every boundary
 * ("speaks-cuts-speaks-cuts") because element handoff isn't sample-accurate.
 *
 * So we schedule every window on ONE shared Web Audio timeline (see
 * gapless-player.js), each clip starting exactly where the previous ended.
 * This plays the stream seamlessly. We fall back to HTMLAudioElement only if
 * Web Audio is unavailable.
 */

import { scheduleChunk, stopGapless } from "@/lib/gapless-player.js";

function hasWebAudio() {
  return (
    typeof window !== "undefined" &&
    !!(window.AudioContext || window.webkitAudioContext)
  );
}

/**
 * Play one audio chunk.
 *
 * @param {object} chunk        - chunk descriptor from voice-streaming
 * @param {string} chunk.audio_b64
 * @param {string} [chunk.mime_type]  - defaults to audio/mpeg
 * @param {HTMLAudioElement} [chunk._preloaded] - prefetched element (HTML fallback only)
 * @param {object} [opts]
 * @param {() => boolean} [opts.shouldAbort]    - called before play; true cancels
 * @param {(audio: HTMLAudioElement|null) => void} [opts.onPlay]
 *        - called once playback/scheduling starts. For the gapless path there
 *          is no HTMLAudioElement, so we pass null.
 */
export async function playAudioChunk(chunk, opts = {}) {
  if (!chunk?.audio_b64) return;
  if (opts.shouldAbort?.()) return;

  // Preferred path: gapless Web Audio scheduling. scheduleChunk resolves once
  // the window is scheduled (right after the previous one), so consecutive
  // windows queue back-to-back with no gap.
  if (hasWebAudio()) {
    const res = await scheduleChunk(chunk.audio_b64, chunk.mime_type);
    if (res) {
      // No HTMLAudioElement in this path; signal "playing" so callers that
      // track an active element for stop-buttons still update their phase.
      opts.onPlay?.(null);
      // Resolve roughly when this window finishes so the caller's playChain
      // stays paced with audio (prevents scheduling thousands of clips at once
      // and lets abort checks run between windows). We cap the wait so a
      // dropped window can't stall the chain.
      const waitMs = Math.min(Math.max(res.duration * 1000, 50), 4000);
      await new Promise((r) => setTimeout(r, waitMs));
      return;
    }
    // fall through to HTML audio if scheduling failed
  }

  // Fallback: HTMLAudioElement (older browsers / decode failure).
  const audio =
    chunk._preloaded ||
    new Audio(`data:${chunk.mime_type || "audio/mpeg"};base64,${chunk.audio_b64}`);

  if (audio.readyState < 2) {
    try { audio.load(); } catch { /* ignore */ }
  }

  await new Promise((resolve) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      resolve();
    };
    audio.onended = finish;
    audio.onerror = finish;
    audio.onpause = finish;
    audio.play()
      .then(() => { opts.onPlay?.(audio); })
      .catch(finish);
  });
}

/** Stop any gapless audio currently scheduled/playing. */
export function stopAudioPlayback() {
  try { stopGapless(); } catch { /* ignore */ }
}
