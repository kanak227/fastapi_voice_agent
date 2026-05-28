#!/bin/bash
# One-time GCP project setup script
# Run this once before the first deployment

set -e

# ── Config ────────────────────────────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT:-your-project-id}"
REGION="${GCP_REGION:-us-central1}"

echo "Setting up GCP project: $PROJECT_ID in $REGION"

# ── Enable APIs ───────────────────────────────────────────────────────────────
echo "Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  --project="$PROJECT_ID"

# ── Create Artifact Registry ──────────────────────────────────────────────────
echo "Creating Artifact Registry..."
gcloud artifacts repositories create chatbot \
  --repository-format=docker \
  --location="$REGION" \
  --description="Chatbot Docker images" \
  --project="$PROJECT_ID" 2>/dev/null || echo "Repository already exists"

# ── Create secrets ────────────────────────────────────────────────────────────
echo ""
echo "Creating secrets in Secret Manager..."
echo "You will be prompted to enter each secret value."
echo ""

create_secret() {
  local name=$1
  local prompt=$2
  echo -n "$prompt: "
  read -s value
  echo ""
  if gcloud secrets describe "$name" --project="$PROJECT_ID" &>/dev/null; then
    echo "$value" | gcloud secrets versions add "$name" --data-file=- --project="$PROJECT_ID"
    echo "  Updated secret: $name"
  else
    echo "$value" | gcloud secrets create "$name" --data-file=- --project="$PROJECT_ID"
    echo "  Created secret: $name"
  fi
}

create_secret "GOOGLE_API_KEY"      "Google API Key (for Gemini)"
create_secret "GEMINI_API_KEY"      "Gemini API Key (same as Google API Key)"
create_secret "DEEPGRAM_API_KEY"    "Deepgram API Key (for STT)"
create_secret "ELEVENLABS_API_KEY"  "ElevenLabs API Key (for TTS)"
create_secret "ELEVENLABS_VOICE_ID" "ElevenLabs Voice ID"
create_secret "QDRANT_URL"          "Qdrant Cloud URL"
create_secret "QDRANT_API_KEY"      "Qdrant API Key"
create_secret "REDIS_URL"           "Redis URL (rediss://...)"

# ── Grant Cloud Build access to secrets ──────────────────────────────────────
echo ""
echo "Granting Cloud Build access to secrets..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

for secret in GOOGLE_API_KEY GEMINI_API_KEY DEEPGRAM_API_KEY ELEVENLABS_API_KEY \
              ELEVENLABS_VOICE_ID QDRANT_URL QDRANT_API_KEY REDIS_URL; do
  gcloud secrets add-iam-policy-binding "$secret" \
    --member="serviceAccount:${CB_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --project="$PROJECT_ID" 2>/dev/null || true
done

# Grant Cloud Build permission to deploy Cloud Run
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/iam.serviceAccountUser"

# ── Connect Cloud Build to GitHub ─────────────────────────────────────────────
echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Connect your GitHub repo to Cloud Build:"
echo "   https://console.cloud.google.com/cloud-build/triggers?project=$PROJECT_ID"
echo ""
echo "2. Create a trigger:"
echo "   - Event: Push to branch (main)"
echo "   - Config: deployment/gcp/cloudbuild.yaml"
echo "   - Substitutions: _REGION=$REGION"
echo ""
echo "3. Or trigger manually:"
echo "   gcloud builds submit --config=deployment/gcp/cloudbuild.yaml \\"
echo "     --substitutions=SHORT_SHA=manual,_REGION=$REGION \\"
echo "     --project=$PROJECT_ID"
