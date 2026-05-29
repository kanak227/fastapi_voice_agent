/**
 * Gapless audio scheduler for the realtime voice pipeline.
 *
 * The backend streams many small (~1s) WAV windows as the TTS model renders
 * them. Playing each one through a separate HTMLAudioElement leaves an audible
 * gap at every boundary ("speaks-cuts-speaks-cuts"), because each element has
 * start latency and the onended -> next .play() handoff is not sample-accurate.
 *
 * Instead we decode every window into an AudioBuffer and schedule it on ONE
 * shared AudioContext timeline, each clip starting exactly where the previous
 * one ends (a running `nextStartAt` cursor). The Web Audio engine then plays
 * them as one continuous stream with no gaps.
 *
 * Ordering: callers MUST invoke `scheduleChunk` in audio order and await it
 * (the voice pipeline already serializes via its playChain), so the cursor
 * advances in order and windows never overlap or shuffle.
 */

let ctx = null;
let nextStartAt = 0;
const activeSources = new Set();

function getCtx() {
  if (typeof window === "undefined") return null;
  if (!ctx || ctx.state === "closed") {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    ctx = new AC();
    nextStartAt = 0;
  }
  return ctx;
}

function b64ToArrayBuffer(b64) {
  const bin = atob(b64);
  const len = bin.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) bytes[i] = bin.charCodeAt(i);
  return bytes.buffer;
}

/**
 * Decode one window and schedule it immediately after the previously
 * scheduled audio. Resolves once the clip is scheduled (not when it finishes),
 * so the caller can quickly schedule the next window ahead of the playhead.
 *
 * @param {string} audioB64 base64-encoded WAV (or any format decodeAudioData supports)
 * @returns {Promise<{startAt:number,duration:number}|null>}
 */
export async function scheduleChunk(audioB64 /*, mimeType */) {
  const c = getCtx();
  if (!c || !audioB64) return null;
  if (c.state === "suspended") {
    try { await c.resume(); } catch { /* ignore */ }
  }

  let audioBuffer;
  try {
    // decodeAudioData wants its own ArrayBuffer copy; slice() guards against
    // detached-buffer reuse across calls.
    audioBuffer = await c.decodeAudioData(b64ToArrayBuffer(audioB64).slice(0));
  } catch {
    return null; // skip an undecodable window rather than break the stream
  }

  const src = c.createBufferSource();
  src.buffer = audioBuffer;
  src.connect(c.destination);

  // Never schedule in the past. A tiny lead avoids glitches when the cursor
  // has already been consumed (first chunk, or after an underrun).
  const now = c.currentTime;
  const startAt = Math.max(now + 0.03, nextStartAt);
  try {
    src.start(startAt);
  } catch {
    return null;
  }
  nextStartAt = startAt + audioBuffer.duration;

  activeSources.add(src);
  src.onended = () => { activeSources.delete(src); };

  return { startAt, duration: audioBuffer.duration };
}

/** Stop everything currently scheduled/playing and reset the timeline. */
export function stopGapless() {
  for (const s of activeSources) {
    try { s.onended = null; s.stop(); } catch { /* ignore */ }
    try { s.disconnect(); } catch { /* ignore */ }
  }
  activeSources.clear();
  if (ctx) nextStartAt = ctx.currentTime;
}

/** Resolve when all scheduled audio has finished playing. */
export async function whenGaplessIdle() {
  const c = ctx;
  if (!c) return;
  // Wait until the playhead passes the last scheduled end (or everything stopped).
  while (activeSources.size > 0 && c.currentTime < nextStartAt - 0.05) {
    await new Promise((r) => setTimeout(r, 80));
  }
}

export function isGaplessActive() {
  return activeSources.size > 0;
}
