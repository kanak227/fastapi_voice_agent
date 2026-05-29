#!/usr/bin/env bash
set -u
BASE="http://localhost:8000"

echo "=== long english via serena ==="
curl -s -X POST "$BASE/v1/text-to-speech/serena" \
  -H 'Content-Type: application/json' \
  -d '{"text":"Krishna is a principal deity in Hinduism. He is revered as the eighth avatar of Vishnu. He delivered the teachings of the Bhagavad Gita to Arjuna.","language_code":"en"}' \
  -o /tmp/long.out -w 'HTTP %{http_code} size=%{size_download}\n'
echo "--- response head ---"
head -c 300 /tmp/long.out; echo

echo "=== container logs (last 40) ==="
sudo docker logs --tail 40 qwen3-tts 2>&1 | tail -40
