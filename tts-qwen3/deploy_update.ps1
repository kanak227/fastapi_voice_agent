#!/usr/bin/env pwsh
#
# Deploy TTS server updates to GCP VM (PowerShell version)
#

$VM_NAME = "qwen3-tts"
$ZONE = "us-central1-c"
$PROJECT_ID = "fastapi-server-497606"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Deploying TTS Updates to GCP VM" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if VM is running
Write-Host "Checking VM status..." -ForegroundColor Yellow
$vmStatus = gcloud compute instances describe $VM_NAME `
    --zone=$ZONE `
    --project=$PROJECT_ID `
    --format="get(status)"

if ($vmStatus -ne "RUNNING") {
    Write-Host "❌ VM is not running (status: $vmStatus)" -ForegroundColor Red
    Write-Host "Start it with: gcloud compute instances start $VM_NAME --zone=$ZONE"
    exit 1
}

Write-Host "✅ VM is running" -ForegroundColor Green
Write-Host ""

# Copy updated server.py to VM
Write-Host "Uploading updated server.py..." -ForegroundColor Yellow
gcloud compute scp server.py "${VM_NAME}:/tmp/server.py" `
    --zone=$ZONE `
    --project=$PROJECT_ID

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ File uploaded to /tmp" -ForegroundColor Green
} else {
    Write-Host "❌ Upload failed" -ForegroundColor Red
    exit 1
}

# Copy file into the Docker container and restart
Write-Host "Installing updated server.py into container..." -ForegroundColor Yellow
gcloud compute ssh $VM_NAME `
    --zone=$ZONE `
    --project=$PROJECT_ID `
    --command="sudo docker cp /tmp/server.py qwen3-tts:/app/server.py"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ File installed in container" -ForegroundColor Green
} else {
    Write-Host "❌ Installation failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Restart the Docker container
Write-Host "Restarting Docker container..." -ForegroundColor Yellow
gcloud compute ssh $VM_NAME `
    --zone=$ZONE `
    --project=$PROJECT_ID `
    --command="sudo docker restart qwen3-tts"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Service restarted" -ForegroundColor Green
} else {
    Write-Host "❌ Restart failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Wait for container to restart
Write-Host "Waiting for container to restart (20 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 20

# Check if container is healthy
Write-Host "Checking container status..." -ForegroundColor Yellow
$containerStatus = gcloud compute ssh $VM_NAME `
    --zone=$ZONE `
    --project=$PROJECT_ID `
    --command="sudo docker ps --filter name=qwen3-tts --format '{{.Status}}'"

if ($containerStatus -like "*healthy*") {
    Write-Host "✅ Container is healthy" -ForegroundColor Green
    Write-Host "Status: $containerStatus"
} elseif ($containerStatus -like "*Up*") {
    Write-Host "⚠️  Container is up but not healthy yet" -ForegroundColor Yellow
    Write-Host "Status: $containerStatus"
} else {
    Write-Host "❌ Container may have issues" -ForegroundColor Red
    Write-Host "Status: $containerStatus"
}

Write-Host ""

# Get VM IP
$vmIp = gcloud compute instances describe $VM_NAME `
    --zone=$ZONE `
    --project=$PROJECT_ID `
    --format="get(networkInterfaces[0].accessConfigs[0].natIP)"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "✅ Deployment Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "TTS Service URL: " -NoNewline
Write-Host "http://${vmIp}:8000/v1" -ForegroundColor White
Write-Host ""
Write-Host "Test with:" -ForegroundColor Yellow
Write-Host "  curl http://${vmIp}:8000/health" -ForegroundColor White
Write-Host ""
Write-Host "Changes deployed:" -ForegroundColor Cyan
Write-Host "  ✅ Lock timeout (5s) for better multi-user handling" -ForegroundColor White
Write-Host "  ✅ TTS response caching (100 entries, 1hr TTL)" -ForegroundColor White
Write-Host "  ✅ Request superseding improvements" -ForegroundColor White
Write-Host "  ✅ Better error handling for busy service" -ForegroundColor White
Write-Host ""
