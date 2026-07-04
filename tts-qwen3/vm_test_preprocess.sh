#!/usr/bin/env bash
set -u

echo "=== Wait for ready ==="
for i in $(seq 1 60); do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health 2>/dev/null || echo 000)
  [ "$code" = "200" ] && { echo "READY after ~$((i*3))s"; break; }
  sleep 3
done

echo "=== Test 1: Hindi + English words + danda ==="
t0=$(date +%s.%N)
curl -s -o /tmp/t1.pcm -w "HTTP=%{http_code} bytes=%{size_download}\n" \
  -X POST http://localhost:8000/v1/text-to-speech/indic-hindi-female \
  -H "Content-Type: application/json" \
  -d '{"text":"यह एक test है। आपका phone number क्या है? कृपया download करें।","language_code":"hi"}'
t1=$(date +%s.%N)
echo "time=$(echo "$t1-$t0" | bc)s"

echo "=== Test 2: Hindi + numbers + markdown ==="
t0=$(date +%s.%N)
curl -s -o /tmp/t2.pcm -w "HTTP=%{http_code} bytes=%{size_download}\n" \
  -X POST http://localhost:8000/v1/text-to-speech/indic-hindi-female \
  -H "Content-Type: application/json" \
  -d '{"text":"### शुल्क ₹250 है और 18% छूट मिलेगी। Date: 15/08/2025।","language_code":"hi"}'
t1=$(date +%s.%N)
echo "time=$(echo "$t1-$t0" | bc)s"

echo "=== Test 3: Pure Hindi with proper punctuation ==="
t0=$(date +%s.%N)
curl -s -o /tmp/t3.pcm -w "HTTP=%{http_code} bytes=%{size_download}\n" \
  -X POST http://localhost:8000/v1/text-to-speech/indic-hindi-female \
  -H "Content-Type: application/json" \
  -d '{"text":"नमस्ते, आप कैसे हैं? मैं ठीक हूँ। धन्यवाद!","language_code":"hi"}'
t1=$(date +%s.%N)
echo "time=$(echo "$t1-$t0" | bc)s"

echo "=== Check for vocab warnings ==="
sudo docker logs --tail 20 qwen3-tts 2>&1 | grep -i "not found in the vocabulary\|Character\|ERROR\|Traceback" | tail -10
echo "(empty = no warnings = good)"
