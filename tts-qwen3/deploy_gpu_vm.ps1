# Deploy the Qwen3 + MMS TTS service on a Spot T4 GPU VM.
#
# Plan B economics (us-central1):
#   n1-standard-4 SPOT  ~$0.025/hr   (~70% off the on-demand rate)
#   1x NVIDIA T4  SPOT  ~$0.10/hr    (~70% off the on-demand rate)
#   100 GB SSD          ~$0.017/GB-mo
#   Always-on monthly:  ~$95/mo
#
# Spot VMs can be preempted (max 24h life). When that happens, the chatbot
# silently falls back to ElevenLabs because the frontend toggle still routes
# requests through `tts_provider=elevenlabs` for any user that hadn't picked
# Offline. We set --restart-on-failure=true so the VM auto-restarts after
# preemption (with a short wait while GCP frees capacity).
#
# Usage (PowerShell):
#   $env:PROJECT="fastapi-server-497606"
#   .\deploy_gpu_vm.ps1
[CmdletBinding()]
param(
    [string]$Project = $env:PROJECT,
    [string]$Region  = $(if ($env:REGION) { $env:REGION } else { "us-central1" }),
    [string]$Zone    = $(if ($env:ZONE)   { $env:ZONE }   else { "us-central1-c" }),
    [string]$Instance = "qwen3-tts",
    [string]$Machine = "n1-standard-4",
    [int]$DiskGB = 100,
    [int]$Port = 8000,
    [string]$ImageTag
)

$ErrorActionPreference = "Stop"

if (-not $Project) { throw "Set PROJECT env var or pass -Project" }
if (-not $ImageTag) {
    $ImageTag = "$Region-docker.pkg.dev/$Project/chatbot/qwen3-tts:latest"
}

$gcloud = "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
if (-not (Test-Path $gcloud)) { $gcloud = "gcloud" }

Write-Host "==> Project:  $Project" -ForegroundColor Cyan
Write-Host "==> Zone:     $Zone"
Write-Host "==> Instance: $Instance"
Write-Host "==> Image:    $ImageTag"
Write-Host ""

# 1) Build & push the image to Artifact Registry.
Write-Host "[1/4] Building image (tts-qwen3/Dockerfile)" -ForegroundColor Yellow
& $gcloud builds submit --tag $ImageTag --project=$Project tts-qwen3
if ($LASTEXITCODE -ne 0) { throw "image build failed" }

# 2) Create the firewall rule (idempotent).
Write-Host "[2/4] Firewall rule for tcp:$Port" -ForegroundColor Yellow
& $gcloud compute firewall-rules describe allow-qwen-tts --project=$Project 2>$null > $null
if ($LASTEXITCODE -ne 0) {
    & $gcloud compute firewall-rules create allow-qwen-tts `
        --project=$Project `
        --allow="tcp:$Port" `
        --target-tags=qwen-tts `
        --description="Qwen3 TTS API"
}

# 3) Create or replace the Spot T4 VM.
Write-Host "[3/4] Provisioning $Instance ($Machine + 1x T4 Spot)" -ForegroundColor Yellow
& $gcloud compute instances describe $Instance --project=$Project --zone=$Zone 2>$null > $null
if ($LASTEXITCODE -eq 0) {
    Write-Host "    instance exists; deleting first"
    & $gcloud compute instances delete $Instance --project=$Project --zone=$Zone --quiet
}

# Startup script the VM runs on every boot. Pulls the latest image and runs it.
$startup = @"
#!/usr/bin/env bash
set -e
# Wait for nvidia-driver install (Deep Learning VM image handles this).
for i in {1..60}; do
  if nvidia-smi >/dev/null 2>&1; then break; fi
  sleep 5
done
gcloud auth configure-docker $Region-docker.pkg.dev --quiet
docker pull $ImageTag
docker rm -f qwen3-tts >/dev/null 2>&1 || true
docker run -d --name qwen3-tts --restart=always \
    --gpus all \
    -p ${Port}:8000 \
    -v /var/lib/qwen-models:/models \
    $ImageTag
"@

# Write startup script to a temp file (gcloud reads --metadata-from-file).
$tmp = [IO.Path]::GetTempFileName()
Set-Content -Path $tmp -Value $startup -NoNewline -Encoding UTF8

& $gcloud compute instances create $Instance `
    --project=$Project `
    --zone=$Zone `
    --machine-type=$Machine `
    --accelerator="type=nvidia-tesla-t4,count=1" `
    --provisioning-model=SPOT `
    --instance-termination-action=STOP `
    --maintenance-policy=TERMINATE `
    --image-family=common-cu129-ubuntu-2204-nvidia-580 `
    --image-project=deeplearning-platform-release `
    --boot-disk-size="${DiskGB}GB" `
    --boot-disk-type=pd-ssd `
    --metadata="install-nvidia-driver=True" `
    --metadata-from-file="startup-script=$tmp" `
    --tags=qwen-tts `
    --scopes=cloud-platform

Remove-Item $tmp -ErrorAction SilentlyContinue
if ($LASTEXITCODE -ne 0) { throw "instance create failed" }

# 4) Print the IP + next steps.
$ip = (& $gcloud compute instances describe $Instance --project=$Project --zone=$Zone `
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)').Trim()

Write-Host ""
Write-Host "[4/4] Done." -ForegroundColor Green
Write-Host "==> External IP: $ip"
Write-Host "==> Service URL: http://${ip}:${Port}/v1"
Write-Host ""
Write-Host "Model warm-up takes ~3-5 min on first start. Watch logs:" -ForegroundColor Cyan
Write-Host "  & '$gcloud' compute ssh $Instance --project=$Project --zone=$Zone -- 'sudo docker logs -f qwen3-tts'"
Write-Host ""
Write-Host "Once /health returns model_loaded=true, set in Cloud Run:" -ForegroundColor Cyan
Write-Host "  QWEN_TTS_BASE_URL=http://${ip}:${Port}/v1"
Write-Host ""
Write-Host "Spot VMs auto-restart on preemption. To force restart manually:" -ForegroundColor Cyan
Write-Host "  & '$gcloud' compute instances start $Instance --zone=$Zone"
