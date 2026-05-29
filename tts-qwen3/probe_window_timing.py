"""Diagnose audio stutter: compare window ARRIVAL intervals vs each window's
AUDIO DURATION. If a window plays for D seconds but the next arrives later than
D, the player underruns -> audible gap/buffering.
"""
import json, time, base64, io, wave, urllib.request

BASE = "https://multi-bot-server-650841589964.us-central1.run.app"
TENANT = "tenant-demo"

body = {
    "session_id": f"probe-{int(time.time()*1000)}",
    "input_type": "voice",
    "text": "Tell me about Krishna in about four sentences.",
    "domain": "religious",
    "language": "en-US",
    "output_audio": True,
    "tts_provider": "qwen",
    "voice": "serena",
}
req = urllib.request.Request(f"{BASE}/agent/stream", data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json", "X-Tenant-Id": TENANT}, method="POST")

def wav_duration(b64):
    try:
        raw = base64.b64decode(b64)
        with wave.open(io.BytesIO(raw), "rb") as w:
            return w.getnframes() / float(w.getframerate()), w.getframerate()
    except Exception as e:
        return None, None

t0 = time.time()
buf = ""
events = []
prev = None
with urllib.request.urlopen(req, timeout=180) as resp:
    for raw in resp:
        now = time.time() - t0
        buf += raw.decode("utf-8", "replace")
        while "\n\n" in buf:
            block, buf = buf.split("\n\n", 1)
            lines = block.split("\n")
            ev = next((l[6:].strip() for l in lines if l.startswith("event:")), None)
            data = "\n".join(l[5:].lstrip() for l in lines if l.startswith("data:"))
            if ev == "audio":
                try:
                    d = json.loads(data)
                    dur, sr = wav_duration(d.get("audio_b64", ""))
                except Exception:
                    dur, sr = None, None
                interval = None if prev is None else now - prev
                prev = now
                events.append((now, dur, interval, sr))

print(f"{'arrival':>8} {'audio_s':>8} {'gap_since_prev':>14} {'sr':>6}  {'STATUS'}")
total_audio = 0.0
deficit_count = 0
for (now, dur, interval, sr) in events:
    status = ""
    if interval is not None and dur is not None:
        # If the gap since previous arrival exceeds previous window's duration,
        # the player would have run dry. (compare interval to THIS dur is rough;
        # better: cumulative.)
        pass
    total_audio += (dur or 0)
    print(f"{now:8.2f} {('%.2f'%dur) if dur else '   ?':>8} {('%.2f'%interval) if interval is not None else '   -':>14} {str(sr):>6}")

# Cumulative analysis: can playback stay fed if it starts at first arrival?
if events:
    start = events[0][0]
    playhead = start
    underruns = []
    for (now, dur, interval, sr) in events:
        if now > playhead + 0.05:   # audio ran out before this window arrived
            underruns.append((now, now - playhead))
        playhead = max(playhead, now) + (dur or 0)
    wall = events[-1][0] - start
    print(f"\nwindows={len(events)} total_audio={total_audio:.2f}s stream_wall={wall:.2f}s")
    print(f"effective_RTF={total_audio/max(wall,0.01):.2f} (>=1 means production keeps up)")
    print(f"underruns (gaps) if playing from 1st arrival: {len(underruns)}")
    for (t, g) in underruns[:10]:
        print(f"   gap of {g:.2f}s before window arriving at {t:.2f}s")
    # how much prebuffer would avoid all underruns?
    # find max deficit
    playhead = start
    worst = 0.0
    for (now, dur, interval, sr) in events:
        deficit = now - playhead
        if deficit > worst:
            worst = deficit
        playhead = max(playhead, now) + (dur or 0)
    print(f"prebuffer needed to avoid underruns: ~{max(worst,0):.2f}s")
