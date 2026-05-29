#!/usr/bin/env bash
set -u
for i in $(seq 1 90); do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health 2>/dev/null || echo 000)
  if [ "$code" = "200" ]; then
    echo "READY after ~$((i*3))s"
    break
  fi
  sleep 3
done
curl -s http://localhost:8000/health; echo
echo "=== Hindi prosody test on prod :8000 ==="
t0=$(date +%s.%N)
curl -s -o /tmp/prod_hi.pcm -w "HTTP=%{http_code} bytes=%{size_download}\n" \
  -X POST http://localhost:8000/v1/text-to-speech/mms-hindi \
  -H "Content-Type: application/json" \
  -d '{"text":"नमस्ते, यह एक परीक्षण है। आप कैसे हैं? मैं ठीक हूँ।","language_code":"hi"}'
t1=$(date +%s.%N)
echo "synth time: $(echo "$t1-$t0" | bc)s"
