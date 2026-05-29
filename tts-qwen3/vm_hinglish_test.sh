#!/usr/bin/env bash
set -u
BASE="http://localhost:8000"

echo "=== hinglish via mms-hindi (hi-Latn) ==="
curl -s -X POST "$BASE/v1/text-to-speech/mms-hindi" \
  -H 'Content-Type: application/json' \
  -d '{"text":"namaste aap kaise hain","language_code":"hi-Latn"}' \
  -o /tmp/hil.out -w 'HTTP %{http_code} size=%{size_download}\n'
echo "--- response (first 300 chars) ---"
head -c 300 /tmp/hil.out; echo

echo "=== container logs (last 25) ==="
sudo docker logs --tail 25 qwen3-tts 2>&1 | tail -25
