#!/usr/bin/env pwsh
#
# Stop GCP services that cost > $15/month
# Stops: Backend (~$50-100/mo) + TTS VM (~$155/mo)
# Keeps: Frontend (~$0-10/mo, already scales to zero)
# Cost reduction: ~$205-265/month → ~$10-15/month
#

Write-Host ""
Write-Host "Stopping High-Cost GCP Services (>$15/month)..." -ForegroundColor Yellow
Write-Host ""

# Stop Backend (~$50-100/month)
Write-Host "Stopping Multi-Bot Server (~`$50-100/month)..." -ForegroundColor Cyan
gcloud run services update multi-bot-server `
    --region=us-central1 `
    --min-instances=0 `
    --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host "Backend stopped" -ForegroundColor Green
} else {
    Write-Host "Failed to stop backend" -ForegroundColor Red
}

# Stop Qwen TTS VM (~$155/month)
Write-Host ""
Write-Host "Stopping Qwen TTS VM (~`$155/month)..." -ForegroundColor Cyan
gcloud compute instances stop qwen3-tts `
    --zone=us-central1-c `
    --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host "TTS VM stopped" -ForegroundColor Green
} else {
    Write-Host "Failed to stop TTS VM" -ForegroundColor Red
}

# Keep Frontend running (already scales to zero, ~$0-10/month)
Write-Host ""
Write-Host "Frontend kept running (~`$0-10/month, scales to zero)" -ForegroundColor Cyan

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "High-cost services stopped!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Cost reduced to ~`$10-15/month" -ForegroundColor Yellow
Write-Host ""
Write-Host "Services stopped:" -ForegroundColor White
Write-Host "  Backend (Cloud Run)" -ForegroundColor Red
Write-Host "  TTS VM (Compute Engine)" -ForegroundColor Red
Write-Host ""
Write-Host "Services still running:" -ForegroundColor White
Write-Host "  Frontend (scales to zero, minimal cost)" -ForegroundColor Green
Write-Host ""
Write-Host "To start services again, run:" -ForegroundColor Cyan
Write-Host "  .\deployment\gcp\start-services.ps1" -ForegroundColor White
Write-Host ""
