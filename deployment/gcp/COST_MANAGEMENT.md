# GCP Cost Management Guide

Complete guide for stopping, starting, and managing costs for your chatbot infrastructure.

## Current Costs Breakdown

### When Running (Monthly)
- **Multi-Bot Server**: ~$50-100/month (min-instances=1, always running)
- **Qwen TTS VM**: ~$155/month (n1-standard-4 + T4 GPU, preemptible)
- **Frontend**: ~$0-10/month (min-instances=0, scales to zero automatically)
- **Qdrant**: ~$0 (cloud free tier)
- **Redis**: ~$0 (cloud free tier)
- **Deepgram/Gemini**: Pay-per-use (only when used)
- **Storage/Secrets**: ~$1-2/month
- **Total**: **~$205-265/month**

### When High-Cost Services Stopped (Monthly)
Using `stop-services.ps1` (stops services >$15/month):
- **Multi-Bot Server**: ~$0 (stopped, scaled to zero)
- **Qwen TTS VM**: ~$0 (VM stopped)
- **Frontend**: ~$0-10/month (still running, scales to zero)
- **Storage/Secrets**: ~$1-2/month (minimal)
- **Total**: **~$10-15/month**

**Savings: ~$190-255/month** when stopped

---

## Quick Stop/Start Commands

### 🛑 Stop High-Cost Services (>$15/month)

```bash
# Stop Backend (~$50-100/month)
gcloud run services update multi-bot-server --region=us-central1 --min-instances=0 --max-instances=0

# Stop Qwen TTS VM (~$155/month)
gcloud compute instances stop qwen3-tts --zone=us-central1-c

# Frontend stays running (~$0-10/month, already scales to zero)
```

**Result**: Cost drops to ~$10-15/month (frontend + storage)

### ▶️ Start High-Cost Services

```bash
# Start Qwen TTS VM
gcloud compute instances start qwen3-tts --zone=us-central1-c

# Wait for VM to boot (30 seconds)
Start-Sleep -Seconds 30

# Start Backend
gcloud run services update multi-bot-server --region=us-central1 --min-instances=1 --max-instances=4

# Frontend already running (scales to zero automatically)
```

**Result**: All services running, cost ~$205-265/month

---

## Automated Scripts

I've created PowerShell scripts to make this easy with one command!

### Script 1: Stop High-Cost Services (>$15/month)

**File**: `deployment/gcp/stop-services.ps1`

**Stops:**
- ❌ Backend (~$50-100/month)
- ❌ TTS VM (~$155/month)

**Keeps running:**
- ✅ Frontend (~$0-10/month, already scales to zero)

**Result**: Cost drops to ~$10-15/month

```powershell
#!/usr/bin/env pwsh
#
# Stop GCP services that cost > $15/month
#

Write-Host "🛑 Stopping High-Cost GCP Services (>$15/month)..." -ForegroundColor Yellow

# Stop Backend (~$50-100/month)
gcloud run services update multi-bot-server `
    --region=us-central1 `
    --min-instances=0 `
    --max-instances=0 `
    --quiet

# Stop Qwen TTS VM (~$155/month)
gcloud compute instances stop qwen3-tts `
    --zone=us-central1-c `
    --quiet

# Frontend stays running (already scales to zero)

Write-Host "🎉 High-cost services stopped!" -ForegroundColor Green
Write-Host "💰 Cost reduced to ~`$10-15/month" -ForegroundColor Yellow
```

### Script 2: Start High-Cost Services

**File**: `deployment/gcp/start-services.ps1`

```powershell
#!/usr/bin/env pwsh
#
# Start high-cost GCP services
#

Write-Host "▶️  Starting High-Cost GCP Services..." -ForegroundColor Yellow

# Start Qwen TTS VM first (takes time to boot)
gcloud compute instances start qwen3-tts `
    --zone=us-central1-c `
    --quiet

Write-Host "⏳ Waiting for VM to boot..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Start Backend
gcloud run services update multi-bot-server `
    --region=us-central1 `
    --min-instances=1 `
    --max-instances=4 `
    --quiet

# Frontend already configured (scales to zero)

Write-Host "🎉 High-cost services started!" -ForegroundColor Green
Write-Host "💰 Cost: ~`$205-265/month while running" -ForegroundColor Yellow
```

### Script 3: Check Status

**File**: `deployment/gcp/check-status.ps1`

```powershell
#!/usr/bin/env pwsh
#
# Check status of all GCP services
#

Write-Host "📊 Checking GCP Services Status..." -ForegroundColor Yellow
Write-Host ""

# Check Backend
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Multi-Bot Server (Backend)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan

$backend = gcloud run services describe multi-bot-server --region=us-central1 --format=json | ConvertFrom-Json

$backendStatus = $backend.status.conditions | Where-Object { $_.type -eq "Ready" } | Select-Object -ExpandProperty status
$backendMinInstances = $backend.spec.template.metadata.annotations.'autoscaling.knative.dev/minScale'
$backendMaxInstances = $backend.spec.template.metadata.annotations.'autoscaling.knative.dev/maxScale'

Write-Host "URL:          $($backend.status.url)" -ForegroundColor White
Write-Host "Status:       $(if ($backendStatus -eq 'True') { '✅ Running' } else { '❌ Not Ready' })" -ForegroundColor $(if ($backendStatus -eq 'True') { 'Green' } else { 'Red' })
Write-Host "Min Instance: $backendMinInstances" -ForegroundColor White
Write-Host "Max Instance: $backendMaxInstances" -ForegroundColor White
Write-Host "Cost:         $(if ($backendMinInstances -gt 0) { '~$50-100/month' } else { '~$0/month (scaled to zero)' })" -ForegroundColor Yellow

# Check Frontend
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Frontend" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan

$frontend = gcloud run services describe chatbot-frontend --region=us-central1 --format=json | ConvertFrom-Json

$frontendStatus = $frontend.status.conditions | Where-Object { $_.type -eq "Ready" } | Select-Object -ExpandProperty status
$frontendMinInstances = $frontend.spec.template.metadata.annotations.'autoscaling.knative.dev/minScale'
$frontendMaxInstances = $frontend.spec.template.metadata.annotations.'autoscaling.knative.dev/maxScale'

Write-Host "URL:          $($frontend.status.url)" -ForegroundColor White
Write-Host "Status:       $(if ($frontendStatus -eq 'True') { '✅ Running' } else { '❌ Not Ready' })" -ForegroundColor $(if ($frontendStatus -eq 'True') { 'Green' } else { 'Red' })
Write-Host "Min Instance: $frontendMinInstances" -ForegroundColor White
Write-Host "Max Instance: $frontendMaxInstances" -ForegroundColor White
Write-Host "Cost:         $(if ($frontendMinInstances -gt 0) { '~$10-20/month' } else { '~$0-10/month (scales to zero)' })" -ForegroundColor Yellow

# Check Qwen TTS VM
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Qwen TTS VM" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan

$vm = gcloud compute instances describe qwen3-tts --zone=us-central1-c --format=json | ConvertFrom-Json

Write-Host "Name:         $($vm.name)" -ForegroundColor White
Write-Host "Status:       $(if ($vm.status -eq 'RUNNING') { '✅ Running' } else { '🛑 Stopped' })" -ForegroundColor $(if ($vm.status -eq 'RUNNING') { 'Green' } else { 'Red' })
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
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "Summary" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""

$totalCost = 0
if ($backendMinInstances -gt 0) { $totalCost += 75 }
if ($frontendMinInstances -gt 0) { $totalCost += 15 }
if ($vm.status -eq 'RUNNING') { $totalCost += 155 }

Write-Host "Estimated Monthly Cost: ~`$$totalCost/month" -ForegroundColor Yellow
Write-Host ""

if ($totalCost -eq 0) {
    Write-Host "✅ All services stopped (zero cost mode)" -ForegroundColor Green
} elseif ($totalCost -lt 50) {
    Write-Host "⚠️  Some services running (partial cost)" -ForegroundColor Yellow
} else {
    Write-Host "💰 All services running (full cost)" -ForegroundColor Cyan
}

Write-Host ""
```

---

## Usage Instructions

### Stop High-Cost Services (Save Money)

```powershell
# Navigate to project
cd "c:\New folder (6)\MAIN"

# Run stop script (stops services >$15/month)
.\deployment\gcp\stop-services.ps1
```

**Stops:**
- Backend (~$50-100/month)
- TTS VM (~$155/month)

**Keeps running:**
- Frontend (~$0-10/month, already scales to zero)

**When to use:**
- End of day/week when not actively developing
- When not expecting traffic
- During vacations/breaks
- When testing is complete

**Cost impact:** Saves ~$190-255/month (drops to ~$10-15/month)

### Start Services (Resume Operation)

```powershell
# Navigate to project
cd "c:\New folder (6)\MAIN"

# Run start script (starts high-cost services)
.\deployment\gcp\start-services.ps1
```

**Starts:**
- Backend (~$50-100/month)
- TTS VM (~$155/month)
- Frontend (already running, ~$0-10/month)

**When to use:**
- Beginning of work day
- Before demo/presentation
- When expecting traffic
- For testing/development

**Wait time:** ~30-60 seconds for everything to be ready

### Check Status

```powershell
# Navigate to project
cd "c:\New folder (6)\MAIN"

# Run status script
.\deployment\gcp\check-status.ps1
```

**Shows:**
- Service URLs
- Running status
- Instance configuration
- Estimated monthly cost

---

## Manual Control (Individual Services)

### Backend Only

```bash
# Stop
gcloud run services update multi-bot-server --region=us-central1 --min-instances=0 --max-instances=0

# Start
gcloud run services update multi-bot-server --region=us-central1 --min-instances=1 --max-instances=4
```

**Saves:** ~$50-100/month when stopped

### Qwen TTS VM Only

```bash
# Stop
gcloud compute instances stop qwen3-tts --zone=us-central1-c

# Start
gcloud compute instances start qwen3-tts --zone=us-central1-c
```

**Saves:** ~$155/month when stopped

### Frontend Only

Frontend already scales to zero automatically (min-instances=0). No manual control needed.

**Cost**: ~$0-10/month (only pay when someone uses it)

---

## Cost Optimization Strategies

### Strategy 1: Low-Cost Mode (Recommended for Development)
**When:** Daily development, low traffic  
**Setup:**
- Backend: Stopped (scales to zero)
- Frontend: Running (already scales to zero)
- TTS VM: Stopped (use ElevenLabs API if needed)
**Cost:** ~$10-15/month

```bash
# Use the stop script
.\deployment\gcp\stop-services.ps1
```

### Strategy 2: Production Mode (Current)
**When:** Live traffic, users  
**Setup:**
- Backend: min=1, max=4 (high availability)
- Frontend: min=0, max=4 (scales to zero)
- TTS VM: Running
**Cost:** ~$205-265/month

```bash
# Use the start script
.\deployment\gcp\start-services.ps1
```

---

## Billing Alerts

Set up budget alerts to avoid surprises:

```bash
# Create budget alert for $300/month
gcloud billing budgets create \
  --billing-account=YOUR_BILLING_ACCOUNT_ID \
  --display-name="Chatbot Monthly Budget" \
  --budget-amount=300 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

You'll receive email alerts at 50%, 90%, and 100% of budget.

---

## Cost Monitoring

### View Current Month Costs

```bash
# Get current costs
gcloud billing projects describe PROJECT_ID --format="value(billingAccountName)"
```

Or visit: https://console.cloud.google.com/billing

### View by Service

Navigate to:
1. Cloud Console → Billing → Reports
2. Filter by:
   - Cloud Run (backend + frontend)
   - Compute Engine (TTS VM)
   - Cloud Storage (images, logs)
   - Other services

---

## Deletion (Complete Removal)

⚠️ **Warning:** This permanently deletes everything!

```bash
# Delete Cloud Run services
gcloud run services delete multi-bot-server --region=us-central1 --quiet
gcloud run services delete chatbot-frontend --region=us-central1 --quiet

# Delete TTS VM
gcloud compute instances delete qwen3-tts --zone=us-central1-c --quiet

# Delete container images
gcloud artifacts docker images delete us-central1-docker.pkg.dev/fastapi-server-497606/chatbot/multi-bot-server --quiet
gcloud artifacts docker images delete us-central1-docker.pkg.dev/fastapi-server-497606/chatbot/frontend --quiet

# Delete secrets (optional)
gcloud secrets delete QWEN_TTS_BASE_URL --quiet
gcloud secrets delete GEMINI_API_KEY --quiet
# ... and so on
```

**Cost after deletion:** ~$0/month (only external services like Qdrant/Redis if still active)

---

## FAQ

### Q: How long does it take to stop services?
**A:** ~10-30 seconds for each service

### Q: How long does it take to start services?
**A:** ~30-60 seconds (VM boot time is the slowest)

### Q: Do I lose data when stopping services?
**A:** No! All data is preserved:
- Database data
- Secrets
- Container images
- Configuration

### Q: What about the frontend when backend is stopped?
**A:** Frontend stays accessible but API calls will fail. Users will see errors if they try to use the chatbot.

### Q: Can I stop just the TTS VM and use ElevenLabs instead?
**A:** Yes! Just stop the VM manually. Frontend will fall back to ElevenLabs (if API key is valid)

### Q: What happens if someone accesses the site when backend is stopped?
**A:** They'll see the frontend UI but chat/voice features won't work (API errors)

### Q: How do I know if services are stopped?
**A:** Run `.\deployment\gcp\check-status.ps1`

### Q: Why not stop frontend too?
**A:** Frontend already scales to zero and costs almost nothing (~$0-10/month). Keeping it running means users can still see the UI.

---

## Quick Reference

| Action | Command | Time | Cost Impact |
|--------|---------|------|-------------|
| Stop High-Cost | `.\deployment\gcp\stop-services.ps1` | 30s | Save $190-255/mo → $10-15/mo |
| Start High-Cost | `.\deployment\gcp\start-services.ps1` | 60s | Cost $205-265/mo |
| Check Status | `.\deployment\gcp\check-status.ps1` | 5s | None |
| Stop Backend Only | `gcloud run services update multi-bot-server --min-instances=0 --max-instances=0 --region=us-central1` | 10s | Save $50-100/mo |
| Stop TTS VM Only | `gcloud compute instances stop qwen3-tts --zone=us-central1-c` | 20s | Save $155/mo |

---

## Recommendation

**For daily development:**
- Use **stop-services.ps1** at end of each day (saves $6-8/day)
- Use **start-services.ps1** at start of work (ready in 60 seconds)
- **Savings:** ~$180-240/month vs keeping everything running 24/7

**For production:**
- Keep backend + TTS VM running 24/7
- Frontend already scales to zero automatically
- Set up billing alerts
- Monitor usage regularly with **check-status.ps1**
