/**
 * Shared audio chunk player for the voice pipeline.
 *
 * Each chunk arriving from `voice-streaming.js` may already carry a
 * pre-decoded Audio element on `_preloaded`. Using it directly skips
 * the data-URL parse delay that otherwise causes audible pauses
 * between back-to-back chunks (especially noticeable with the offline
 * Qwen3 service which emits one fully-rendered clip per sentence).
 */

/**
 * Play one audio chunk.
 *
 * @param {object} chunk        - chunk descriptor from voice-streaming
 * @param {string} chunk.audio_b64
 * @param {string} [chunk.mime_type]  - defaults to audio/mpeg
 * @param {HTMLAudioElement} [chunk._preloaded] - prefetched element
 * @param {object} [opts]
 * @param {() => boolean} [opts.shouldAbort]    - called before play; true cancels
 * @param {(audio: HTMLAudioElement) => void} [opts.onPlay]
 *        - called immediately after play() succeeds. Useful to track
 *          the active audio for stop buttons.
 */
export async function playAudioChunk(chunk, opts = {}) {
  if (!chunk?.audio_b64) return;
  if (opts.shouldAbort?.()) return;

  const audio =
    chunk._preloaded ||
    new Audio(`data:${chunk.mime_type || "audio/mpeg"};base64,${chunk.audio_b64}`);

  // Some browsers throttle decoding for off-screen documents; force load.
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
