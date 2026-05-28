#!/usr/bin/env bash
# Boot script for the Qwen3 TTS VM. Runs on every start (incl. preempt restart).
# Idempotent: skips work that's already done.
set -e

LOG=/var/log/qwen3-startup.log
exec > >(tee -a "$LOG") 2>&1

echo "==> $(date) starting"

# 1. Install Docker if missing.
if ! command -v docker >/dev/null 2>&1; then
  echo "==> installing docker"
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi

# 2. Install NVIDIA Container Toolkit so docker --gpus works.
if ! dpkg -l nvidia-container-toolkit >/dev/null 2>&1; then
  echo "==> installing nvidia-container-toolkit"
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
      gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
  curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
      sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
      tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
  apt-get update
  apt-get install -y nvidia-container-toolkit
  nvidia-ctk runtime configure --runtime=docker
  systemctl restart docker
fi

# 3. Wait for the GPU to be ready.
for i in {1..60}; do
  if nvidia-smi >/dev/null 2>&1; then break; fi
  echo "==> waiting for nvidia-smi ($i/60)"
  sleep 5
done

# 4. Pull image and run.
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet || true
IMAGE="us-central1-docker.pkg.dev/fastapi-server-497606/chatbot/qwen3-tts:latest"
docker pull "$IMAGE"
docker rm -f qwen3-tts >/dev/null 2>&1 || true
docker run -d --name qwen3-tts --restart=always \
    --gpus all \
    -p 8000:8000 \
    -v /var/lib/qwen-models:/models \
    -e QWEN_DTYPE=float32 \
    "$IMAGE"

echo "==> $(date) done"
