#!/usr/bin/env bash
# Validate the new /v1/text-to-speech-stream endpoint inside the container on :8001
set -u
echo "=== copy updated server.py ==="
sudo docker cp /tmp/server_new.py qwen3-tts:/app/server_new.py

echo "=== (re)launch on :8001 ==="
sudo docker exec qwen3-tts bash -c 'pkill -f "server_new:app" 2>/dev/null; sleep 1' || true
sudo docker exec -d qwen3-tts bash -c 'cd /app && PORT=8001 python -m uvicorn server_new:app --host 0.0.0.0 --port 8001 > /tmp/newsrv.log 2>&1'

echo "=== wait ready ==="
for i in $(seq 1 90); do
  code=$(sudo docker exec qwen3-tts bash -c 'curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health' 2>/dev/null || echo 000)
  [ "$code" = "200" ] && { echo "ready after ~$((i*3))s"; break; }
  sleep 3
done

echo "=== streaming endpoint: measure time-to-first-byte + frame arrival ==="
sudo docker exec qwen3-tts bash -c 'cat > /tmp/probe_stream.py << "PYEOF"
import time, json, urllib.request
body=json.dumps({"text":"Krishna is a principal deity in Hinduism. He is revered as the eighth avatar of Vishnu.","language_code":"en"}).encode()
req=urllib.request.Request("http://localhost:8001/v1/text-to-speech-stream/serena",data=body,headers={"Content-Type":"application/json"},method="POST")
t0=time.time(); first=None; total=0; frames=0
with urllib.request.urlopen(req,timeout=120) as r:
    sr=r.headers.get("X-Sample-Rate")
    while True:
        b=r.read(8192)
        if not b: break
        if first is None: first=time.time()-t0
        total+=len(b); frames+=1
dur=time.time()-t0
samples=total//2
print(f"sample_rate={sr}")
print(f"time-to-first-byte={first*1000:.0f}ms")
print(f"total_bytes={total} samples={samples} audio={samples/int(sr):.2f}s wall={dur:.2f}s read_calls={frames}")
PYEOF
python /tmp/probe_stream.py'

echo "=== MMS via stream endpoint ==="
sudo docker exec qwen3-tts bash -c 'curl -s -o /tmp/s_mms.pcm -D - -X POST http://localhost:8001/v1/text-to-speech-stream/mms-hindi -H "Content-Type: application/json" -d "{\"text\":\"नमस्ते\",\"language_code\":\"hi\"}" 2>/dev/null | grep -i "x-sample-rate\|x-engine"; echo "bytes=$(stat -c%s /tmp/s_mms.pcm)"'
