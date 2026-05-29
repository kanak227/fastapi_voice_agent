#!/usr/bin/env bash
set -u
IMG="us-central1-docker.pkg.dev/fastapi-server-497606/chatbot/qwen3-tts:latest"

echo "### Restoring container with QWEN_DTYPE=float32 (fastest working on T4) ..."
sudo docker rm -f qwen3-tts >/dev/null 2>&1 || true
sudo docker run -d --name qwen3-tts --restart=always \
    --gpus all \
    -e QWEN_DTYPE=float32 \
    -p 8000:8000 \
    -v /var/lib/qwen-models:/models \
    "$IMG" >/dev/null
echo "waiting for model load..."
for i in $(seq 1 60); do
  if curl -sf http://localhost:8000/health | grep -q '"loaded":true'; then
    echo "loaded after ~$((i*5))s"; break
  fi
  sleep 5
done
curl -s http://localhost:8000/health | grep -o '"dtype":"[^"]*"'
echo

bench() {
  local label="$1"; local voice="$2"; local lang="$3"; local text="$4"
  echo "=== $label ==="
  for i in 1 2; do
    local t0=$(date +%s.%N)
    local code=$(curl -s -o /tmp/b.out -w '%{http_code}' -X POST "http://localhost:8000/v1/text-to-speech/$voice" \
      -H 'Content-Type: application/json' \
      -d "{\"text\":\"$text\",\"language_code\":\"$lang\"}")
    local t1=$(date +%s.%N)
    local sz=$(stat -c%s /tmp/b.out 2>/dev/null || echo 0)
    echo "  run $i: HTTP $code  $(echo "$t1 - $t0" | bc)s  bytes=$sz"
  done
}

# MMS Hindi (the "works fine" engine) — warm it once, then time.
bench "MMS Hindi warmup+time" "mms-hindi" "hi" "नमस्ते, यह एक परीक्षण वाक्य है। कृष्ण एक देवता हैं।"
# Qwen short first chunk
bench "Qwen serena short (~6 words)" "serena" "en" "Krishna is a Hindu deity."
# MMS English (facebook/mms-tts-eng) — does our map support it? routes via base 'en' -> qwen. skip.
