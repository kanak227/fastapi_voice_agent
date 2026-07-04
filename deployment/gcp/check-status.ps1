#!/usr/bin/env pwsh
#
# Check status of all GCP services
#

Write-Host ""
Write-Host "Checking GCP Services Status..." -ForegroundColor Yellow
Write-Host ""

# Check Backend
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Multi-Bot Server (Backend)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$backend = gcloud run services describe multi-bot-server --region=us-central1 --format=json | ConvertFrom-Json

$backendStatus = $backend.status.conditions | Where-Object { $_.type -eq "Ready" } | Select-Object -ExpandProperty status
$backendMinInstances = $backend.spec.template.metadata.annotations.'autoscaling.knative.dev/minScale'
$backendMaxInstances = $backend.spec.template.metadata.annotations.'autoscaling.knative.dev/maxScale'

Write-Host "URL:          $($backend.status.url)" -ForegroundColor White
Write-Host "Status:       $(if ($backendStatus -eq 'True') { 'Running' } else { 'Not Ready' })" -ForegroundColor $(if ($backendStatus -eq 'True') { 'Green' } else { 'Red' })
Write-Host "Min Instance: $backendMinInstances" -ForegroundColor White
Write-Host "Max Instance: $backendMaxInstances" -ForegroundColor White
Write-Host "Cost:         $(if ($backendMinInstances -gt 0) { '~$50-100/month' } else { '~$0/month (scaled to zero)' })" -ForegroundColor Yellow

# Check Frontend
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Frontend" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$frontend = gcloud run services describe chatbot-frontend --region=us-central1 --format=json | ConvertFrom-Json

$frontendStatus = $frontend.status.conditions | Where-Object { $_.type -eq "Ready" } | Select-Object -ExpandProperty status
$frontendMinInstances = $frontend.spec.template.metadata.annotations.'autoscaling.knative.dev/minScale'
$frontendMaxInstances = $frontend.spec.template.metadata.annotations.'autoscaling.knative.dev/maxScale'

Write-Host "URL:          $($frontend.status.url)" -ForegroundColor White
Write-Host "Status:       $(if ($frontendStatus -eq 'True') { 'Running' } else { 'Not Ready' })" -ForegroundColor $(if ($frontendStatus -eq 'True') { 'Green' } else { 'Red' })
Write-Host "Min Instance: $frontendMinInstances" -ForegroundColor White
Write-Host "Max Instance: $frontendMaxInstances" -ForegroundColor White
Write-Host "Cost:         $(if ($frontendMinInstances -gt 0) { '~$10-20/month' } else { '~$0-10/month (scales to zero)' })" -ForegroundColor Yellow

# Check Qwen TTS VM
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Qwen TTS VM" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$vm = gcloud compute instances describe qwen3-tts --zone=us-central1-c --format=json | ConvertFrom-Json

Write-Host "Name:         $($vm.name)" -ForegroundColor White
Write-Host "Status:       $(if ($vm.status -eq 'RUNNING') { 'Running' } else { 'Stopped' })" -ForegroundColor $(if ($vm.status -eq 'RUNNING') { 'Green' } else { 'Red' })
Write-Host "Machine Type: $($vm.machineType.Split('/')[-1])" -ForegroundColor White
Write-Host "Zone:         $($vm.zone.Split('/')[-1])" -ForegroundColor White

if ($vm.status -eq 'RUNNING') {
    $ip = $vm.networkInterfaces[0].accessConfigs[0].natIP
    Write-Host "External IP:  $ip" -ForegroundColor White
    Write-Host "Endpoint:     http://${ip}:8000/v1" -ForegroundColor White
    Write-Host "Cost:         ~$155/month (running)" -ForegroundColor Yellow
} else {
    Write-Host "Cost:         ~$0/month (stopped)" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Summary" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

$totalCost = 0
if ($backendMinInstances -gt 0) { $totalCost += 75 }
if ($frontendMinInstances -gt 0) { $totalCost += 15 }
if ($vm.status -eq 'RUNNING') { $totalCost += 155 }

Write-Host "Estimated Monthly Cost: ~`$$totalCost/month" -ForegroundColor Yellow
Write-Host ""

if ($totalCost -eq 0) {
    Write-Host "All services stopped (zero cost mode)" -ForegroundColor Green
    Write-Host ""
    Write-Host "To start services, run:" -ForegroundColor Cyan
    Write-Host "  .\deployment\gcp\start-services.ps1" -ForegroundColor White
} elseif ($totalCost -lt 50) {
    Write-Host "Some services running (partial cost)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To stop all services, run:" -ForegroundColor Cyan
    Write-Host "  .\deployment\gcp\stop-services.ps1" -ForegroundColor White
} else {
    Write-Host "All services running (full cost)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To stop services when not in use, run:" -ForegroundColor Cyan
    Write-Host "  .\deployment\gcp\stop-services.ps1" -ForegroundColor White
}

Write-Host ""
