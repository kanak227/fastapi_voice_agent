#!/usr/bin/env bash
set -e
# Wait for nvidia-driver install (Deep Learning VM image handles this).
for i in {1..60}; do
  if nvidia-smi >/dev/null 2>&1; then break; fi
  sleep 5
done

# The cu129 Deep Learning VM image does NOT ship Docker preinstalled.
# Install it on first boot, then wire up the NVIDIA container runtime.
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
  sh /tmp/get-docker.sh
  nvidia-ctk runtime configure --runtime=docker
  systemctl restart docker
fi

gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
docker pull us-central1-docker.pkg.dev/fastapi-server-497606/chatbot/qwen3-tts:latest
docker rm -f qwen3-tts >/dev/null 2>&1 || true
docker run -d --name qwen3-tts --restart=always \
    --gpus all \
    -p 8000:8000 \
    -v /var/lib/qwen-models:/models \
    us-central1-docker.pkg.dev/fastapi-server-497606/chatbot/qwen3-tts:latest
