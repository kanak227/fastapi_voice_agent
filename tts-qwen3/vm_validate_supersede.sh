#!/usr/bin/env bash
# Validate request-superseding: fire a long request, then a second request
# ~1s later. The first should abort (409 or truncated stream); the second
# should complete fully. Run inside the container on :8001.
set -u
echo "=== copy new server.py ==="
sudo docker cp /tmp/server_new.py qwen3-tts:/app/server_new.py
sudo docker exec qwen3-tts bash -c 'pkill -f "server_new:app" 2>/dev/null; sleep 1' || true
sudo docker exec -d qwen3-tts bash -c 'cd /app && PORT=8001 python -m uvicorn server_new:app --host 0.0.0.0 --port 8001 > /tmp/newsrv.log 2>&1'

echo "=== wait ready ==="
for i in $(seq 1 90); do
  code=$(sudo docker exec qwen3-tts bash -c 'curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health' 2>/dev/null || echo 000)
  [ "$code" = "200" ] && { echo "ready after ~$((i*3))s"; break; }
  sleep 3
done

echo "=== overlapping requests (non-stream): A long, then B 1s later ==="
sudo docker exec qwen3-tts bash -c '
LONG="Krishna is a principal deity in Hinduism. He is revered as the eighth avatar of Vishnu. He delivered the teachings of the Bhagavad Gita to Arjuna on the battlefield of Kurukshetra, guiding him through doubt."
# Request A (long) in background, capture HTTP code
( curl -s -o /tmp/A.out -w "A_HTTP=%{http_code} A_bytes=%{size_download}\n" -X POST http://localhost:8001/v1/text-to-speech/serena -H "Content-Type: application/json" -d "{\"text\":\"$LONG\",\"language_code\":\"en\"}" > /tmp/A.code 2>&1 ) &
APID=$!
sleep 1.0
# Request B (short) — should supersede A
curl -s -o /tmp/B.out -w "B_HTTP=%{http_code} B_bytes=%{size_download}\n" -X POST http://localhost:8001/v1/text-to-speech/serena -H "Content-Type: application/json" -d "{\"text\":\"Hello there.\",\"language_code\":\"en\"}" > /tmp/B.code 2>&1
wait $APID
echo "--- Request A (older, expect 409 superseded) ---"; cat /tmp/A.code
echo "--- Request B (newer, expect 200) ---"; cat /tmp/B.code
'

echo "=== server log tail (look for seq + superseded) ==="
sudo docker exec qwen3-tts bash -c 'grep -E "seq=|superseded" /tmp/newsrv.log | tail -15'
