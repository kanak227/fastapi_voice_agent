/**
 * Shared audio chunk player for the voice pipeline.
 *
 * The realtime backend streams many small WAV windows. Playing each through a
 * separate HTMLAudioElement leaves audible gaps; even a just-in-time Web Audio
 * scheduler stutters because windows arrive with jitter and multi-second gaps
 * between sentences.
 *
 * So we hand every window to a PREBUFFERED gapless scheduler (gapless-player.js)
 * that decodes + queues windows and only starts playback once a small cushion
 * exists, then renders them contiguously on one timeline. We fall back to
 * HTMLAudioElement only if Web Audio is unavailable.
 */

import {
  scheduleChunk,
  stopGapless,
  whenGaplessIdle,
  flushGapless,
} from "@/lib/gapless-player.js";

function hasWebAudio() {
  return (
    typeof window !== "undefined" &&
    !!(window.AudioContext || window.webkitAudioContext)
  );
}

/**
 * Enqueue one audio window for gapless playback.
 *
 * @param {object} chunk
 * @param {string} chunk.audio_b64
 * @param {string} [chunk.mime_type]
 * @param {object} [opts]
 * @param {() => boolean} [opts.shouldAbort]
 * @param {(audio: HTMLAudioElement|null) => void} [opts.onPlay]
 */
export async function playAudioChunk(chunk, opts = {}) {
  if (!chunk?.audio_b64) return;
  if (opts.shouldAbort?.()) return;

  if (hasWebAudio()) {
    // Just decode + enqueue. The prebuffered pump handles pacing/scheduling,
    // so we return quickly and let the caller feed the next window. This keeps
    // the queue ahead of the playhead and absorbs arrival jitter.
    const res = await scheduleChunk(chunk.audio_b64, chunk.mime_type);
    if (res) {
      opts.onPlay?.(null);
      return;
    }
    // fall through to HTML audio if decode failed
  }

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

/**
 * Wait until all enqueued/scheduled gapless audio has finished playing.
 * Call this after the SSE stream ends so the turn doesn't resolve while audio
 * is still in the buffer.
 */
export async function waitForAudioToFinish() {
  if (!hasWebAudio()) return;
  try { await whenGaplessIdle(); } catch { /* ignore */ }
}

/** Start playback of whatever is queued even if the prebuffer wasn't reached. */
export function flushAudioPlayback() {
  if (!hasWebAudio()) return;
  try { flushGapless(); } catch { /* ignore */ }
}

/** Stop any gapless audio currently scheduled/playing. */
export function stopAudioPlayback() {
  try { stopGapless(); } catch { /* ignore */ }
}
