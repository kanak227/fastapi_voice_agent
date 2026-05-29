"""Profile the voice pipeline phase-by-phase against the deployed backend.

Streams /agent/stream (input_type=voice with text, so STT is skipped) and
timestamps every SSE event relative to request start. Reports:
  - LLM time-to-first-token
  - LLM total streaming time
  - TTS time-to-first-audio (first spoken chunk ready)
  - per-chunk TTS gaps
  - total wall time
Run for both tts_provider=qwen and elevenlabs (if available), and for a short
and a longer reply.
"""
import json
import time
import urllib.request

BASE = "https://multi-bot-server-650841589964.us-central1.run.app"
TENANT = "tenant-demo"


def profile(label, text, tts_provider, voice=None, language="en-US"):
    body = {
        "session_id": f"prof-{int(time.time()*1000)}",
        "input_type": "voice",
        "text": text,
        "domain": "religious",
        "language": language,
        "output_audio": True,
        "tts_provider": tts_provider,
    }
    if voice:
        body["voice"] = voice
        body["tts_voice"] = voice

    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}/agent/stream",
        data=data,
        headers={"Content-Type": "application/json", "X-Tenant-Id": TENANT},
        method="POST",
    )

    t0 = time.time()
    first_text = None
    last_text = None
    audio_times = []
    final_text_t = None
    done_t = None

    buf = ""
    with urllib.request.urlopen(req, timeout=300) as resp:
        for raw in resp:
            now = time.time() - t0
            buf += raw.decode("utf-8", "replace")
            while "\n\n" in buf:
                block, buf = buf.split("\n\n", 1)
                ev = None
                for line in block.split("\n"):
                    if line.startswith("event:"):
                        ev = line[6:].strip()
                if ev == "text":
                    if first_text is None:
                        first_text = now
                    last_text = now
                elif ev == "audio":
                    audio_times.append(now)
                elif ev == "final_text":
                    final_text_t = now
                elif ev == "done":
                    done_t = now

    total = time.time() - t0
    print(f"\n=== {label}  (provider={tts_provider} voice={voice}) ===")
    print(f"  input chars              : {len(text)}")
    print(f"  LLM first token          : {first_text:.2f}s" if first_text else "  LLM first token          : n/a")
    print(f"  LLM last token           : {last_text:.2f}s" if last_text else "  LLM last token           : n/a")
    if first_text is not None and last_text is not None:
        print(f"  LLM stream duration      : {last_text - first_text:.2f}s")
    print(f"  audio chunks             : {len(audio_times)}")
    if audio_times:
        print(f"  1st audio ready          : {audio_times[0]:.2f}s")
        if first_text is not None:
            print(f"  TTS lead (1st audio - 1st text): {audio_times[0] - first_text:.2f}s")
        gaps = [audio_times[i] - audio_times[i-1] for i in range(1, len(audio_times))]
        if gaps:
            print(f"  per-chunk gaps           : {[f'{g:.2f}' for g in gaps]}")
            print(f"  avg chunk gap            : {sum(gaps)/len(gaps):.2f}s")
    print(f"  final_text               : {final_text_t:.2f}s" if final_text_t else "")
    print(f"  done                     : {done_t:.2f}s" if done_t else "")
    print(f"  TOTAL wall               : {total:.2f}s")


if __name__ == "__main__":
    SHORT = "Who is Krishna? Answer in one short sentence."
    LONG = "Tell me about Krishna in about four sentences."

    # Qwen (offline) — the slow path the user cares about
    profile("SHORT / Qwen", SHORT, "qwen", voice="serena")
    profile("LONG / Qwen", LONG, "qwen", voice="serena")

    # Hindi via MMS (fast engine) for comparison
    profile("LONG / Qwen Hindi(MMS)", "कृष्ण के बारे में चार वाक्यों में बताइए।", "qwen", voice="mms-hindi", language="hi")
