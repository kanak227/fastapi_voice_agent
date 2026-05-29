#!/usr/bin/env bash
set -u
IMG="us-central1-docker.pkg.dev/fastapi-server-497606/chatbot/qwen3-tts:latest"
echo "removing old container..."
sudo docker rm -f qwen3-tts >/dev/null 2>&1 || true
echo "starting with QWEN_AUTOCAST=false ..."
sudo docker run -d --name qwen3-tts --restart=always \
    --gpus all \
    -e QWEN_AUTOCAST=false \
    -p 8000:8000 \
    -v /var/lib/qwen-models:/models \
    "$IMG" >/dev/null
for i in $(seq 1 60); do
  if curl -sf http://localhost:8000/health | grep -q '"loaded":true'; then
    echo "loaded after ~$((i*5))s"; break
  fi
  sleep 5
done
echo "=== synth test (autocast off) ==="
curl -s -X POST http://localhost:8000/v1/text-to-speech/serena \
  -H 'Content-Type: application/json' \
  -d '{"text":"Krishna is a Hindu deity.","language_code":"en"}' \
  -o /tmp/t.out -w 'HTTP %{http_code} size=%{size_download}\n'
