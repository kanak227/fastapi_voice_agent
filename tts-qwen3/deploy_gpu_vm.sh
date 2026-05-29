#!/usr/bin/env bash
# Deploy the Qwen3 TTS service on a Compute Engine T4 GPU VM.
#
# Costs (us-central1, on-demand):
#   n1-standard-4  ~$0.19/hr
#   1x NVIDIA T4   ~$0.35/hr
#   100GB SSD      ~$0.017/GB-month
#   Total:         ~$0.54/hr running, ~$390/mo if always on
#
# To save, stop the VM when not in use (`gcloud compute instances stop`).
#
# Usage:
#   PROJECT=fastapi-server-497606 ZONE=us-central1-c bash deploy_gpu_vm.sh

set -euo pipefail

PROJECT="${PROJECT:-fastapi-server-497606}"
ZONE="${ZONE:-us-central1-c}"        # T4 quota is per-zone; -c usually has it
INSTANCE="${INSTANCE:-qwen3-tts}"
MACHINE="${MACHINE:-n1-standard-4}"
DISK_GB="${DISK_GB:-100}"
PORT="${PORT:-8000}"
IMAGE_TAG="${IMAGE_TAG:-us-central1-docker.pkg.dev/${PROJECT}/chatbot/qwen3-tts:latest}"

echo "==> Project: ${PROJECT}"
echo "==> Zone: ${ZONE}"
echo "==> Instance: ${INSTANCE}"

# 1. Build & push image to Artifact Registry.
gcloud builds submit --tag "${IMAGE_TAG}" --project="${PROJECT}" .

# 2. Create the VM with a T4 and the Deep Learning VM image (CUDA + drivers preinstalled).
gcloud compute instances create "${INSTANCE}" \
    --project="${PROJECT}" \
    --zone="${ZONE}" \
    --machine-type="${MACHINE}" \
    --accelerator="type=nvidia-tesla-t4,count=1" \
    --maintenance-policy=TERMINATE \
    --image-family=common-cu129-ubuntu-2204-nvidia-580 \
    --image-project=deeplearning-platform-release \
    --boot-disk-size="${DISK_GB}GB" \
    --boot-disk-type=pd-ssd \
    --metadata="install-nvidia-driver=True" \
    --tags=qwen-tts \
    --scopes=cloud-platform

# 3. Open the port.
gcloud compute firewall-rules create allow-qwen-tts \
    --project="${PROJECT}" \
    --allow="tcp:${PORT}" \
    --target-tags=qwen-tts \
    --description="Qwen3 TTS API" || true

# 4. Start the container on the VM.
#    The cu129 Deep Learning VM image does NOT ship Docker preinstalled, so
#    install it (plus the NVIDIA container runtime) if it's missing.
gcloud compute ssh "${INSTANCE}" --project="${PROJECT}" --zone="${ZONE}" --command "
set -e
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
  sudo sh /tmp/get-docker.sh
  sudo nvidia-ctk runtime configure --runtime=docker
  sudo systemctl restart docker
fi
sudo gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
sudo docker pull ${IMAGE_TAG}
sudo docker rm -f qwen3-tts || true
sudo docker run -d --name qwen3-tts --restart=always \
    --gpus all \
    -p ${PORT}:8000 \
    -v /var/lib/qwen-models:/models \
    ${IMAGE_TAG}
"

EXTERNAL_IP=$(gcloud compute instances describe "${INSTANCE}" \
    --project="${PROJECT}" --zone="${ZONE}" \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo
echo "==> Service should be reachable at: http://${EXTERNAL_IP}:${PORT}"
echo "==> Update fastapi_server/.env:"
echo "       ELEVENLABS_BASE_URL=http://${EXTERNAL_IP}:${PORT}/v1"
echo "       ELEVENLABS_VOICE_ID=serena"
echo
echo "Model warm-up takes ~3-5 min on first start. Watch with:"
echo "   gcloud compute ssh ${INSTANCE} --zone=${ZONE} -- 'sudo docker logs -f qwen3-tts'"
