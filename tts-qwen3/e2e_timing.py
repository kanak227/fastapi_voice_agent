"""Measure end-to-end voice timing through Cloud Run with the new engine."""
import json, time, urllib.request

BASE = "https://multi-bot-server-650841589964.us-central1.run.app"
TENANT = "tenant-demo"

body = {
    "session_id": f"e2e-{int(time.time()*1000)}",
    "input_type": "voice",
    "text": "Who is Krishna? Answer in two short sentences.",
    "domain": "religious",
    "language": "en-US",
    "output_audio": True,
    "tts_provider": "qwen",
    "voice": "serena",
}
req = urllib.request.Request(f"{BASE}/agent/stream", data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json", "X-Tenant-Id": TENANT}, method="POST")

t0 = time.time()
first_text = first_audio = None
audio_times = []
buf = ""
with urllib.request.urlopen(req, timeout=180) as resp:
    for raw in resp:
        now = time.time() - t0
        buf += raw.decode("utf-8", "replace")
        while "\n\n" in buf:
            block, buf = buf.split("\n\n", 1)
            ev = next((l[6:].strip() for l in block.split("\n") if l.startswith("event:")), None)
            if ev == "text" and first_text is None:
                first_text = now
            elif ev == "audio":
                if first_audio is None:
                    first_audio = now
                audio_times.append(now)

total = time.time() - t0
print(f"LLM first token   : {first_text:.2f}s" if first_text else "no text")
print(f"1st audio chunk   : {first_audio:.2f}s" if first_audio else "no audio")
print(f"audio chunks      : {len(audio_times)}  at {[f'{t:.1f}' for t in audio_times]}")
print(f"TOTAL             : {total:.2f}s")
