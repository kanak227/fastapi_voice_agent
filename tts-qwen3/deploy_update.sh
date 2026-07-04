#!/bin/bash
#
# Deploy TTS server updates to GCP VM
# This script:
# 1. Copies updated server.py to the VM
# 2. Restarts the TTS service
# 3. Verifies it's running
#

set -e

VM_NAME="qwen3-tts"
ZONE="us-central1-c"
PROJECT_ID=${GCLOUD_PROJECT:-"fastapi-server-497606"}

echo "=========================================="
echo "Deploying TTS Updates to GCP VM"
echo "=========================================="
echo ""

# Check if VM is running
echo "Checking VM status..."
VM_STATUS=$(gcloud compute instances describe $VM_NAME \
  --zone=$ZONE \
  --project=$PROJECT_ID \
  --format="get(status)")

if [ "$VM_STATUS" != "RUNNING" ]; then
    echo "❌ VM is not running (status: $VM_STATUS)"
    echo "Start it with: gcloud compute instances start $VM_NAME --zone=$ZONE"
    exit 1
fi

echo "✅ VM is running"
echo ""

# Copy updated server.py to VM
echo "Uploading updated server.py..."
gcloud compute scp server.py $VM_NAME:/home/harsh_gupta_tekurious_in/tts-qwen3/server.py \
  --zone=$ZONE \
  --project=$PROJECT_ID

echo "✅ File uploaded"
echo ""

# Restart the TTS service
echo "Restarting TTS service..."
gcloud compute ssh $VM_NAME \
  --zone=$ZONE \
  --project=$PROJECT_ID \
  --command="sudo systemctl restart qwen-tts"

echo "✅ Service restarted"
echo ""

# Wait for service to start
echo "Waiting for service to start (10 seconds)..."
sleep 10

# Check service status
echo "Checking service status..."
gcloud compute ssh $VM_NAME \
  --zone=$ZONE \
  --project=$PROJECT_ID \
  --command="sudo systemctl status qwen-tts --no-pager | head -20"

echo ""

# Get VM IP
VM_IP=$(gcloud compute instances describe $VM_NAME \
  --zone=$ZONE \
  --project=$PROJECT_ID \
  --format="get(networkInterfaces[0].accessConfigs[0].natIP)")

echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "TTS Service URL: http://${VM_IP}:8000/v1"
echo ""
echo "Test with:"
echo "  curl http://${VM_IP}:8000/health"
echo ""
echo "Changes deployed:"
echo "  - Lock timeout (5s) for better multi-user handling"
echo "  - TTS response caching (100 entries, 1hr TTL)"
echo "  - Request superseding improvements"
echo "  - Better error handling for busy service"
echo ""
