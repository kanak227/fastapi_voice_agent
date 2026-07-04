/**
 * Prebuffered gapless audio scheduler for the realtime voice pipeline.
 *
 * The backend streams many small WAV windows as the TTS model renders them.
 * Two things make naive playback stutter:
 *   1. Windows arrive with jitter (e.g. +0.66s then +1.32s for ~1s of audio),
 *      so a just-in-time scheduler underruns and clicks mid-sentence.
 *   2. Between sentences the LLM pauses, leaving multi-second arrival gaps.
 *
 * To stay smooth we behave like a media player: decode each window into an
 * AudioBuffer, queue it, and only START playback once a PREBUFFER cushion is
 * ready. Once playing, every window is scheduled exactly where the previous
 * one ends (a running `nextStartAt` cursor) so the Web Audio engine renders
 * one continuous stream. If the buffer drains (a long LLM gap), we re-enter
 * buffering and resume cleanly instead of glitching.
 *
 * Ordering: callers MUST enqueue windows in audio order (the voice pipeline
 * serializes via its playChain), so the queue and cursor stay in order.
 */

const PREBUFFER_SEC = 2.0;   // cushion before first sound (absorbs jitter)
const REBUFFER_SEC = 1.2;    // cushion required to resume after an underrun

let ctx = null;
let nextStartAt = 0;          // AudioContext time where the next clip should start
let queue = [];               // decoded AudioBuffers waiting to be scheduled
let buffered = 0;             // seconds of audio currently queued (not yet scheduled)
let started = false;          // have we begun playback for this turn?
let draining = false;         // pump loop running?
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

function _scheduleBuffer(c, audioBuffer) {
  const src = c.createBufferSource();
  src.buffer = audioBuffer;
  src.connect(c.destination);
  // Keep the cursor ahead of the playhead; if it fell behind (underrun), start
  // a hair in the future so the first sample isn't clipped.
  const startAt = Math.max(c.currentTime + 0.02, nextStartAt);
  try {
    src.start(startAt);
  } catch {
    return;
  }
  nextStartAt = startAt + audioBuffer.duration;
  activeSources.add(src);
  src.onended = () => { activeSources.delete(src); };
}

/**
 * Pump loop: schedules queued buffers contiguously while keeping a cushion.
 * Starts only after PREBUFFER_SEC is available, then drains the queue. If the
 * queue empties mid-turn it waits for REBUFFER_SEC before resuming.
 */
async function _pump() {
  if (draining) return;
  draining = true;
  const c = getCtx();
  if (!c) { draining = false; return; }
  if (c.state === "suspended") { try { await c.resume(); } catch {} }

  try {
    while (true) {
      // Need an initial cushion before the very first clip.
      if (!started && buffered < PREBUFFER_SEC && queue.length > 0) {
        // wait for more windows unless the turn is clearly tiny (handled on finalize)
        await new Promise((r) => setTimeout(r, 60));
        if (!queue.length && !started) { /* nothing yet */ }
        continue;
      }
      if (queue.length === 0) {
        // Drained. DO NOT stop playback if already started - keep the stream open
        // for more chunks to arrive. Only break to wait for more audio.
        break; // nothing to schedule right now; new enqueues will re-pump
      }

      // If resuming after an underrun, wait for a small cushion again.
      if (!started && buffered < REBUFFER_SEC && queue.length > 0) {
        // allow start if this is the tail (no more coming) — finalize() flushes
        await new Promise((r) => setTimeout(r, 60));
        continue;
      }

      const buf = queue.shift();
      buffered -= buf.duration;
      if (!started) {
        started = true;
        // anchor the timeline slightly ahead of now for the first clip
        nextStartAt = Math.max(nextStartAt, c.currentTime + 0.05);
      }
      _scheduleBuffer(c, buf);
    }
  } finally {
    draining = false;
  }
}

/**
 * Decode + enqueue one window. Resolves quickly (after decode), so the caller
 * can feed the next window. Playback pacing is handled by the pump loop.
 *
 * @param {string} audioB64 base64 WAV
 * @returns {Promise<{duration:number}|null>}
 */
export async function scheduleChunk(audioB64 /*, mimeType */) {
  const c = getCtx();
  if (!c || !audioB64) return null;
  if (c.state === "suspended") { try { await c.resume(); } catch {} }

  let audioBuffer;
  try {
    audioBuffer = await c.decodeAudioData(b64ToArrayBuffer(audioB64).slice(0));
  } catch {
    return null; // skip undecodable window
  }

  queue.push(audioBuffer);
  buffered += audioBuffer.duration;
  _pump();
  return { duration: audioBuffer.duration };
}

/**
 * Force-start playback even if the prebuffer threshold wasn't reached (called
 * when the turn has ended and no more windows are coming, so a short reply
 * isn't held back waiting for a cushion it will never get).
 */
export function flushGapless() {
  started = false; // let pump start with whatever is queued
  // Temporarily allow start by faking enough buffer via direct pump with low bar:
  // simplest: if there is anything queued, mark as startable.
  if (queue.length > 0) {
    // lower the bar: pump treats started transition; emulate by setting buffered
    // high enough to pass thresholds for this drain.
    buffered = Math.max(buffered, PREBUFFER_SEC);
  }
  _pump();
}

/** Stop everything and reset for the next turn. */
export function stopGapless() {
  for (const s of activeSources) {
    try { s.onended = null; s.stop(); } catch {}
    try { s.disconnect(); } catch {}
  }
  activeSources.clear();
  queue = [];
  buffered = 0;
  started = false;
  draining = false;
  if (ctx) nextStartAt = ctx.currentTime;
}

/** Resolve when all queued + scheduled audio has finished playing. */
export async function whenGaplessIdle() {
  const c = ctx;
  if (!c) return;
  // Make sure anything still queued gets played out.
  flushGapless();
  // Wait for all audio to finish - don't break early
  while (queue.length > 0 || activeSources.size > 0) {
    await new Promise((r) => setTimeout(r, 100));
  }
  // Give a tiny grace period for the last audio to truly finish
  if (c && c.currentTime < nextStartAt) {
    const remaining = Math.max(0, (nextStartAt - c.currentTime) * 1000);
    if (remaining > 0 && remaining < 5000) {
      await new Promise((r) => setTimeout(r, remaining + 50));
    }
  }
}

export function isGaplessActive() {
  return activeSources.size > 0 || queue.length > 0;
}
