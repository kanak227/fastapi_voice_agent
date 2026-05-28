# Deployment Guide — Google Cloud Run

## Architecture (merged backend)

Two Cloud Run services. The gateway and all 10 domain bots run inside a
single container so there's only one always-on process to pay for.

```
Internet
   │
   ├── chatbot-frontend  (Next.js, port 3000, scale-to-zero)
   │        │
   │        └── multi-bot-server  (gateway + 10 bots, port 8080, min=1)
   │                  │
   │                  ├─ FastAPI gateway routes:  /agent/*, /voice/*, /health, ...
   │                  └─ 10 bot subprocesses:     127.0.0.1:8001..8010
```

Bot subprocesses are reached over loopback (no network hop, no auth).
The merged container is the only place that needs to stay warm.

## Cost

| Service | Resources | Monthly cost |
|---|---|---|
| `multi-bot-server` (merged) | 2 vCPU, 3 GiB, min=1 | ~$33 |
| `chatbot-frontend` | 1 vCPU, 0.5 GiB, min=0 | ~$0-5 |
| Artifact Registry, secrets, egress | | ~$2-5 |

**Idle baseline: ~$33-43/month.** Plus per-request CPU during real traffic
(usually +$5-15). Free tier of 2M requests / 360k vCPU-seconds covers
moderate traffic for free.

## Quick start

### 1. One-time setup

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
cd deployment/gcp
chmod +x setup.sh
./setup.sh
```

This enables APIs, creates the Artifact Registry repo, and provisions
secrets in Secret Manager.

### 2. Deploy

```bash
gcloud builds submit \
  --config=deployment/gcp/cloudbuild.yaml \
  --substitutions=SHORT_SHA=$(git rev-parse --short HEAD),_REGION=us-central1 \
  --project=YOUR_PROJECT_ID
```

Or wire the Cloud Build trigger to your GitHub repo (push to `main` →
auto-deploy).

### 3. Service URLs

```bash
gcloud run services describe chatbot-frontend \
  --region=us-central1 --format='value(status.url)'
gcloud run services describe multi-bot-server \
  --region=us-central1 --format='value(status.url)'
```

## Environment

### Secrets (Secret Manager)

| Secret | Used by |
|---|---|
| `GEMINI_API_KEY`, `GOOGLE_API_KEY` | LLM calls |
| `DEEPGRAM_API_KEY` | STT |
| `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` | Online TTS |
| `QDRANT_URL`, `QDRANT_API_KEY` | Vector store |
| `REDIS_URL` | Short-term memory + retrieval cache |

Future (when GPU TTS comes online):

| Secret | Notes |
|---|---|
| `QWEN_TTS_BASE_URL` | Compute Engine VM URL, e.g. `http://1.2.3.4:8000/v1` |
| `QWEN_TTS_API_KEY` | Optional shared secret |

### Plain env vars (set in cloudbuild.yaml)

`LLM_PROVIDER=gemini`, `GEMINI_MODEL=gemini-2.0-flash`,
`FASTAPI_TENANT_ID=tenant-demo`, `ENV=production`. The merged container
sets `DOMAIN_MAP_JSON` to loopback URLs automatically — no override needed.

## Local development

```bash
# All bots + gateway in one process (mirrors production)
cd tekurious-chatbot-main/bots
PYTHONPATH=../../fastapi_server:. python multi_bot_server/merged_main.py

# Frontend (separate terminal)
cd tekurious-chatbot-main/tekurious-chatbot-ui
npm run dev
```

Or, for finer-grained dev with hot reload, run the gateway and bots as
separate uvicorn processes (`scripts/start_local_domain_bots.ps1`).

## Updating secrets

```bash
# Add a new version
echo -n "new-value" | gcloud secrets versions add SECRET_NAME --data-file=-

# Redeploy to pick it up (Cloud Run pins to the version at deploy time)
gcloud run services update multi-bot-server --region=us-central1 \
  --update-labels=secret-rev=$(date +%s)
```
