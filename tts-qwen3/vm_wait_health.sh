#!/usr/bin/env bash
# Poll the prod TTS container health until ready, then print health + verify
# the superseding code path is present in the running server.
set -u
for i in $(seq 1 90); do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health 2>/dev/null || echo 000)
  if [ "$code" = "200" ]; then
    echo "READY after ~$((i*3))s"
    break
  fi
  sleep 3
done
echo "=== health ==="
curl -s http://localhost:8000/health; echo
echo "=== superseding present in image? ==="
sudo docker exec qwen3-tts grep -c "RequestSuperseded" /app/server.py
echo "=== container image + status ==="
sudo docker ps --filter name=qwen3-tts --format '{{.Image}} {{.Status}}'
