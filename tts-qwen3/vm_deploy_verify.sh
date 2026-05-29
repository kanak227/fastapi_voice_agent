#!/usr/bin/env bash
# Pull the faster-qwen3-tts image, restart prod container on :8000, verify.
set -u
IMG="us-central1-docker.pkg.dev/fastapi-server-497606/chatbot/qwen3-tts:latest"

sudo gcloud auth configure-docker us-central1-docker.pkg.dev --quiet >/dev/null 2>&1
echo "=== pulling new image ==="
sudo docker pull "$IMG" | tail -2
sudo docker rm -f qwen3-tts >/dev/null 2>&1 || true
sudo docker run -d --name qwen3-tts --restart=always \
    --gpus all \
    -p 8000:8000 \
    -v /var/lib/qwen-models:/models \
    "$IMG" >/dev/null

echo "=== wait for ready (model load + CUDA graph warmup) ==="
for i in $(seq 1 90); do
  if curl -sf http://localhost:8000/health | grep -q '"status":"ok"'; then
    echo "ready after ~$((i*3))s"; break
  fi
  sleep 3
done
curl -s http://localhost:8000/health; echo

py_time() {
  # $1 label, $2 voice, $3 lang, $4 text
  python3 - "$2" "$3" "$4" "$1" << 'PYEOF'
import sys, time, json, urllib.request
voice, lang, text, label = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
body=json.dumps({"text":text,"language_code":lang}).encode()
req=urllib.request.Request(f"http://localhost:8000/v1/text-to-speech/{voice}",data=body,headers={"Content-Type":"application/json"},method="POST")
t0=time.time()
with urllib.request.urlopen(req,timeout=120) as r:
    data=r.read()
print(f"  {label}: {time.time()-t0:.2f}s  bytes={len(data)}  HTTP {r.status}")
PYEOF
}

echo "=== timed synth (real wall time) ==="
py_time "serena short" serena en "Krishna is the eighth avatar of Vishnu."
py_time "serena long" serena en "Krishna is a principal deity in Hinduism. He is revered as the eighth avatar of Vishnu. He delivered the teachings of the Bhagavad Gita to Arjuna."
py_time "ryan short" ryan en "Krishna is the eighth avatar of Vishnu."
py_time "mms hindi" mms-hindi hi "नमस्ते, यह एक परीक्षण है।"
