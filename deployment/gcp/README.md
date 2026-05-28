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
