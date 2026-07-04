# Google Cloud deployment

The chatbot runs on **two Cloud Run services**:

| Service | Resources | Min instances | Notes |
|---|---|---|---|
| `multi-bot-server` | 2 vCPU / 3 GiB | 1 (always warm) | Gateway + 10 bot subprocesses in one container |
| `chatbot-frontend` | 1 vCPU / 0.5 GiB | 0 (scale-to-zero) | Next.js |

## Cost

- Merged backend: **~$33/mo** idle baseline (always warm)
- Frontend: ~$0-5/mo (free for low traffic; you can also host this on
  Vercel for free)
- Artifact Registry + Secret Manager + egress: ~$2-5/mo

**Total: ~$35-40/mo.** Adding the offline TTS GPU service is a separate
Compute Engine VM (see `tts-qwen3/deploy_gpu_vm.sh`).

## Why one merged service?

- Each Cloud Run service with `min-instances=1` burns ~$13/mo for the idle
  baseline alone. Two warm services is ~$26/mo just sitting still.
- Gateway and bots talk constantly. Co-locating them means no
  service-to-service auth, no cross-region latency, no double network hop.
- Bot subprocesses are I/O-bound (waiting on Gemini), so 2 vCPU is enough
  to run all 10 of them concurrently.

## Prereqs

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com \
  artifactregistry.googleapis.com cloudbuild.googleapis.com \
  secretmanager.googleapis.com
```

## Deploy

```bash
cd deployment/gcp
chmod +x setup.sh
./setup.sh                          # one-time: secrets + repo

gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=SHORT_SHA=$(git rev-parse --short HEAD) \
  --project=YOUR_PROJECT_ID
```

## Required secrets

| Secret | Used by |
|---|---|
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | LLM |
| `DEEPGRAM_API_KEY` | STT |
| `ELEVENLABS_API_KEY` / `ELEVENLABS_VOICE_ID` | Online TTS |
| `QDRANT_URL` / `QDRANT_API_KEY` | Vector store |
| `REDIS_URL` | Memory + cache |

When the GPU TTS service is deployed, also create:

| Secret | Notes |
|---|---|
| `QWEN_TTS_BASE_URL` | Public URL of the T4 VM, e.g. `http://1.2.3.4:8000/v1` |
| `QWEN_TTS_API_KEY` | Optional pre-shared key |

Then add `QWEN_TTS_BASE_URL=QWEN_TTS_BASE_URL:latest` and
`QWEN_TTS_API_KEY=QWEN_TTS_API_KEY:latest` to the `--set-secrets` line in
`cloudbuild.yaml` and redeploy.


---

## Cost Management Scripts

### Quick Commands

Three PowerShell scripts for easy cost control:

#### 1. Stop High-Cost Services (>$15/month)
```powershell
.\deployment\gcp\stop-services.ps1
```

**Stops:**
- ❌ Backend (~$50-100/month)
- ❌ TTS VM (~$155/month)

**Keeps running:**
- ✅ Frontend (~$0-10/month, already scales to zero)

**Result**: Cost drops to ~$10-15/month

#### 2. Start High-Cost Services
```powershell
.\deployment\gcp\start-services.ps1
```

**Starts:**
- ✅ Backend
- ✅ TTS VM

**Wait time**: ~30-60 seconds

**Result**: All services operational, cost ~$205-265/month

#### 3. Check Service Status
```powershell
.\deployment\gcp\check-status.ps1
```

**Shows**: Current status and estimated monthly cost

---

### Cost Breakdown

#### Full Operation (~$205-265/month)
- Backend: ~$50-100/month (always-on, min=1)
- TTS VM: ~$155/month (n1-standard-4 + T4 GPU)
- Frontend: ~$0-10/month (scales to zero)
- Storage: ~$1-2/month

#### Low-Cost Mode (~$10-15/month)
After running `stop-services.ps1`:
- Backend: ~$0 (stopped)
- TTS VM: ~$0 (stopped)
- Frontend: ~$0-10/month (still running)
- Storage: ~$1-2/month

**Monthly Savings: ~$190-255**

---

### Daily Workflow Example

**Morning** (start work):
```powershell
.\deployment\gcp\start-services.ps1
# Wait 60 seconds, then start working
```

**Evening** (end work):
```powershell
.\deployment\gcp\stop-services.ps1
# Saves ~$6-8 overnight
```

**Anytime** (check status):
```powershell
.\deployment\gcp\check-status.ps1
```

---

### Why Frontend Stays Running?

Frontend has `min-instances=0` and scales to zero automatically:
- Costs only ~$0-10/month
- Users can still access the UI
- Chat/voice features won't work when backend is stopped

Since it costs almost nothing, we keep it running!

---

### Manual Control Commands

If you need individual service control:

**Stop Backend**:
```bash
gcloud run services update multi-bot-server \
  --region=us-central1 --min-instances=0 --max-instances=0
```

**Stop TTS VM**:
```bash
gcloud compute instances stop qwen3-tts --zone=us-central1-c
```

**Start Backend**:
```bash
gcloud run services update multi-bot-server \
  --region=us-central1 --min-instances=1 --max-instances=4
```

**Start TTS VM**:
```bash
gcloud compute instances start qwen3-tts --zone=us-central1-c
```

---

### Full Documentation

For complete details, see:
- **COST_MANAGEMENT.md** - Complete cost management guide
- **COST_CONTROL_SUMMARY.md** (root folder) - Quick summary
- **DEPLOYMENT_STATUS.md** (root folder) - Current deployment status

---

### Summary

✅ **Simple**: One command to stop/start high-cost services  
✅ **Fast**: ~60 seconds to restart everything  
✅ **Safe**: No data loss, everything preserved  
✅ **Smart**: Only stops services >$15/month  
✅ **Saves**: ~$190-255/month when stopped  

**Recommendation**: Stop services at end of each workday, restart in morning. Save ~$180-240/month vs 24/7 operation.
