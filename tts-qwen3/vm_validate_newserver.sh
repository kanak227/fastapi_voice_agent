#!/usr/bin/env bash
# Validate the rewritten server.py inside the running container (which already
# has faster-qwen3-tts installed) on port 8001, without disturbing prod (8000).
set -u

echo "=== copy new server.py into container as server_new.py ==="
sudo docker cp /tmp/server_new.py qwen3-tts:/app/server_new.py

echo "=== launch on :8001 in background ==="
sudo docker exec -d qwen3-tts bash -c 'cd /app && PORT=8001 python -m uvicorn server_new:app --host 0.0.0.0 --port 8001 > /tmp/newsrv.log 2>&1'

echo "=== wait for model load + graph warmup ==="
for i in $(seq 1 90); do
  code=$(sudo docker exec qwen3-tts bash -c 'curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health' 2>/dev/null || echo 000)
  if [ "$code" = "200" ]; then
    st=$(sudo docker exec qwen3-tts bash -c 'curl -s http://localhost:8001/health' 2>/dev/null)
    echo "$st" | grep -q '"status":"ok"' && { echo "ready after ~$((i*3))s"; break; }
  fi
  sleep 3
done
sudo docker exec qwen3-tts bash -c 'curl -s http://localhost:8001/health'; echo

echo
echo "=== timed synth: serena EN (short) ==="
sudo docker exec qwen3-tts bash -c 't0=$(date +%s.%N); code=$(curl -s -o /tmp/n1.out -w "%{http_code}" -X POST http://localhost:8001/v1/text-to-speech/serena -H "Content-Type: application/json" -d "{\"text\":\"Krishna is the eighth avatar of Vishnu.\",\"language_code\":\"en\"}"); t1=$(date +%s.%N); echo "HTTP $code  $(echo "$t1-$t0"|bc)s  bytes=$(stat -c%s /tmp/n1.out)"'

echo "=== timed synth: ryan EN (voice differs) ==="
sudo docker exec qwen3-tts bash -c 't0=$(date +%s.%N); code=$(curl -s -o /tmp/n2.out -w "%{http_code}" -X POST http://localhost:8001/v1/text-to-speech/ryan -H "Content-Type: application/json" -d "{\"text\":\"Krishna is the eighth avatar of Vishnu.\",\"language_code\":\"en\"}"); t1=$(date +%s.%N); echo "HTTP $code  $(echo "$t1-$t0"|bc)s  bytes=$(stat -c%s /tmp/n2.out)"'

echo "=== timed synth: long EN ==="
sudo docker exec qwen3-tts bash -c 't0=$(date +%s.%N); code=$(curl -s -o /tmp/n3.out -w "%{http_code}" -X POST http://localhost:8001/v1/text-to-speech/serena -H "Content-Type: application/json" -d "{\"text\":\"Krishna is a principal deity in Hinduism. He is revered as the eighth avatar of Vishnu. He delivered the teachings of the Bhagavad Gita to Arjuna.\",\"language_code\":\"en\"}"); t1=$(date +%s.%N); echo "HTTP $code  $(echo "$t1-$t0"|bc)s  bytes=$(stat -c%s /tmp/n3.out)"'

echo "=== MMS Hindi still works ==="
sudo docker exec qwen3-tts bash -c 'curl -s -o /tmp/n4.out -w "HTTP %{http_code} bytes=%{size_download}\n" -X POST http://localhost:8001/v1/text-to-speech/mms-hindi -H "Content-Type: application/json" -d "{\"text\":\"नमस्ते, यह एक परीक्षण है।\",\"language_code\":\"hi\"}"'

echo "=== md5 serena vs ryan (must differ) ==="
sudo docker exec qwen3-tts bash -c 'md5sum /tmp/n1.out /tmp/n2.out'

echo "=== tail new server log ==="
sudo docker exec qwen3-tts bash -c 'tail -15 /tmp/newsrv.log'
