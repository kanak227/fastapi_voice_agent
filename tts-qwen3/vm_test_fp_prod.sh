#!/usr/bin/env bash
# Test FastPitch integration on prod :8000
set -u

echo "=== Wait for ready ==="
for i in $(seq 1 90); do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health 2>/dev/null || echo 000)
  if [ "$code" = "200" ]; then
    echo "READY after ~$((i*3))s"
    break
  fi
  sleep 3
done
curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/health
echo

echo "=== Hindi via FastPitch (new voice ID) ==="
t0=$(date +%s.%N)
curl -s -o /tmp/fp_test1.pcm -w "HTTP=%{http_code} bytes=%{size_download}\n" \
  -X POST http://localhost:8000/v1/text-to-speech/indic-hindi-female \
  -H "Content-Type: application/json" \
  -d '{"text":"नमस्ते, आप कैसे हैं? मैं ठीक हूँ।","language_code":"hi"}'
t1=$(date +%s.%N)
echo "time=$(echo "$t1-$t0" | bc)s"

echo "=== Hindi backward compat (old mms-hindi voice ID) ==="
t0=$(date +%s.%N)
curl -s -o /tmp/fp_test2.pcm -w "HTTP=%{http_code} bytes=%{size_download}\n" \
  -X POST http://localhost:8000/v1/text-to-speech/mms-hindi \
  -H "Content-Type: application/json" \
  -d '{"text":"कृष्ण हिंदू धर्म में एक प्रमुख देवता हैं।","language_code":"hi"}'
t1=$(date +%s.%N)
echo "time=$(echo "$t1-$t0" | bc)s"

echo "=== Tamil ==="
t0=$(date +%s.%N)
curl -s -o /tmp/fp_test3.pcm -w "HTTP=%{http_code} bytes=%{size_download}\n" \
  -X POST http://localhost:8000/v1/text-to-speech/indic-tamil-female \
  -H "Content-Type: application/json" \
  -d '{"text":"வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்?","language_code":"ta"}'
t1=$(date +%s.%N)
echo "time=$(echo "$t1-$t0" | bc)s"

echo "=== English (Qwen still works) ==="
t0=$(date +%s.%N)
curl -s -o /tmp/fp_test4.pcm -w "HTTP=%{http_code} bytes=%{size_download}\n" \
  -X POST http://localhost:8000/v1/text-to-speech/serena \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, how are you?","language_code":"en"}'
t1=$(date +%s.%N)
echo "time=$(echo "$t1-$t0" | bc)s"

echo "=== Voices endpoint ==="
curl -s http://localhost:8000/v1/voices | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d[\"voices\"])} voices'); [print(f'  {v[\"voice_id\"]}') for v in d['voices'][:8]]" 2>/dev/null
