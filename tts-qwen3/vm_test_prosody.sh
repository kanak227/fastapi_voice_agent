#!/usr/bin/env bash
# Test the new MMS prosody-via-silence on port 8001 (non-destructive to prod).
set -u

echo "=== copy + launch new server on :8001 ==="
sudo docker cp /tmp/server_new.py qwen3-tts:/app/server_new.py
sudo docker exec qwen3-tts bash -c 'pkill -f "server_new:app" 2>/dev/null; sleep 1' || true
sudo docker exec -d qwen3-tts bash -c 'cd /app && PORT=8001 python -m uvicorn server_new:app --host 0.0.0.0 --port 8001 > /tmp/newsrv.log 2>&1'

echo "=== wait for ready ==="
for i in $(seq 1 90); do
  code=$(sudo docker exec qwen3-tts bash -c 'curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health' 2>/dev/null || echo 000)
  [ "$code" = "200" ] && { echo "ready after ~$((i*3))s"; break; }
  sleep 3
done

echo "=== Hindi with punctuation (new server - should have pauses) ==="
sudo docker exec qwen3-tts bash -c '
curl -s -o /tmp/hi_new.pcm -w "HTTP=%{http_code} bytes=%{size_download}\n" \
  -X POST http://localhost:8001/v1/text-to-speech/mms-hindi \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"नमस्ते, यह एक परीक्षण है। आप कैसे हैं? मैं ठीक हूँ।\",\"language_code\":\"hi\"}"
'

echo "=== Same text on OLD server :8000 (no pauses) ==="
sudo docker exec qwen3-tts bash -c '
curl -s -o /tmp/hi_old.pcm -w "HTTP=%{http_code} bytes=%{size_download}\n" \
  -X POST http://localhost:8000/v1/text-to-speech/mms-hindi \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"नमस्ते, यह एक परीक्षण है। आप कैसे हैं? मैं ठीक हूँ।\",\"language_code\":\"hi\"}"
'

echo "=== size comparison (new should be LARGER due to silence gaps) ==="
sudo docker exec qwen3-tts bash -c 'echo "NEW: $(stat -c%s /tmp/hi_new.pcm) bytes"; echo "OLD: $(stat -c%s /tmp/hi_old.pcm) bytes"'

echo "=== server log (check for errors) ==="
sudo docker exec qwen3-tts bash -c 'tail -10 /tmp/newsrv.log'
