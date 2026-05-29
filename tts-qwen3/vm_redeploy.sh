#!/usr/bin/env bash
# Pull the freshly-built image and recreate the container on the VM.
set -e
IMG="us-central1-docker.pkg.dev/fastapi-server-497606/chatbot/qwen3-tts:latest"
sudo gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
sudo docker pull "$IMG"
sudo docker rm -f qwen3-tts >/dev/null 2>&1 || true
sudo docker run -d --name qwen3-tts --restart=always \
    --gpus all \
    -p 8000:8000 \
    -v /var/lib/qwen-models:/models \
    "$IMG"
echo "=== container started, waiting for model load ==="
for i in $(seq 1 60); do
  if curl -sf http://localhost:8000/health | grep -q '"loaded":true'; then
    echo "model loaded after ~$((i*5))s"
    break
  fi
  sleep 5
done
curl -s http://localhost:8000/health; echo
