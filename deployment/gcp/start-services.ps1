#!/usr/bin/env pwsh
#
# Start high-cost GCP services (>$15/month)
# Starts: Backend (~$50-100/mo) + TTS VM (~$155/mo)
# Frontend already running (scales to zero, ~$0-10/mo)
# Cost: ~$205-265/month when running
#

Write-Host ""
Write-Host "Starting High-Cost GCP Services..." -ForegroundColor Yellow
Write-Host ""

# Start Qwen TTS VM first (takes time to boot)
Write-Host "Starting Qwen TTS VM (~`$155/month)..." -ForegroundColor Cyan
gcloud compute instances start qwen3-tts `
    --zone=us-central1-c `
    --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host "TTS VM starting (will take ~30 seconds to boot)" -ForegroundColor Green
} else {
    Write-Host "Failed to start TTS VM" -ForegroundColor Red
    exit 1
}

# Wait for VM to boot
Write-Host ""
Write-Host "Waiting for VM to boot..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Verify TTS is responding
Write-Host "Checking TTS service..." -ForegroundColor Cyan
$ttsIp = gcloud compute instances describe qwen3-tts --zone=us-central1-c --format="get(networkInterfaces[0].accessConfigs[0].natIP)"
try {
    $response = Invoke-WebRequest -Uri "http://${ttsIp}:8000/v1/voices" -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "TTS service is ready" -ForegroundColor Green
    }
} catch {
    Write-Host "TTS service not ready yet (will auto-start)" -ForegroundColor Yellow
}

# Start Backend
Write-Host ""
Write-Host "Starting Multi-Bot Server (~`$50-100/month)..." -ForegroundColor Cyan
gcloud run services update multi-bot-server `
    --region=us-central1 `
    --min-instances=1 `
    --max-instances=4 `
    --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host "Backend started" -ForegroundColor Green
} else {
    Write-Host "Failed to start backend" -ForegroundColor Red
}

# Frontend is already configured to scale to zero, no need to modify
Write-Host ""
Write-Host "Frontend already configured (scales to zero, ~`$0-10/month)" -ForegroundColor Cyan

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "High-cost services started!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services running:" -ForegroundColor White
Write-Host "  Backend (Cloud Run, min=1)" -ForegroundColor Green
Write-Host "  TTS VM (Compute Engine)" -ForegroundColor Green
Write-Host "  Frontend (Cloud Run, min=0, scales to zero)" -ForegroundColor Green
Write-Host ""
Write-Host "URLs:" -ForegroundColor Yellow
Write-Host "  Frontend: https://chatbot-frontend-650841589964.us-central1.run.app" -ForegroundColor White
Write-Host "  Backend:  https://multi-bot-server-t5wdyzp3ta-uc.a.run.app" -ForegroundColor White
Write-Host ""
Write-Host "Cost: ~`$205-265/month while running" -ForegroundColor Yellow
Write-Host ""
Write-Host "To stop services, run:" -ForegroundColor Cyan
Write-Host "  .\deployment\gcp\stop-services.ps1" -ForegroundColor White
Write-Host ""
