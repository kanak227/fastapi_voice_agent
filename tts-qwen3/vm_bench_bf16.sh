#!/usr/bin/env bash
set -u
IMG="us-central1-docker.pkg.dev/fastapi-server-497606/chatbot/qwen3-tts:latest"
TEXT='Krishna is a principal deity in Hinduism. He is revered as the eighth avatar of Vishnu.'
SHORT='Krishna is a Hindu deity.'

bench() {
  local label="$1"; local text="$2"
  echo "=== $label ==="
  for i in 1 2; do
    local t0=$(date +%s.%N)
    local code=$(curl -s -o /tmp/b.out -w '%{http_code}' -X POST "http://localhost:8000/v1/text-to-speech/serena" \
      -H 'Content-Type: application/json' \
      -d "{\"text\":\"$text\",\"language_code\":\"en\"}")
    local t1=$(date +%s.%N)
    local sz=$(stat -c%s /tmp/b.out 2>/dev/null || echo 0)
    echo "  run $i: HTTP $code  $(echo "$t1 - $t0" | bc)s  bytes=$sz"
  done
}

echo "### Restarting container with QWEN_DTYPE=bfloat16 ..."
sudo docker rm -f qwen3-tts >/dev/null 2>&1 || true
sudo docker run -d --name qwen3-tts --restart=always \
    --gpus all \
    -e QWEN_DTYPE=bfloat16 \
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

bench "BF16 short (16-word first chunk)" "$SHORT"
bench "BF16 two-sentence" "$TEXT"
