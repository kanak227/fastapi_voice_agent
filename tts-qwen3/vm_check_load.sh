#!/usr/bin/env bash
set -u
echo "=== GPU state ==="
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader 2>/dev/null
echo
echo "=== recent synth timings from container logs ==="
sudo docker logs --tail 200 qwen3-tts 2>&1 | grep -E "synth engine=|POST /v1/text-to-speech" | tail -30
echo
echo "=== isolated single-call timing (no contention) ==="
for i in 1 2; do
  t0=$(date +%s.%N)
  code=$(curl -s -o /tmp/c.out -w '%{http_code}' -X POST http://localhost:8000/v1/text-to-speech/serena \
    -H 'Content-Type: application/json' \
    -d '{"text":"Krishna is the eighth avatar of Vishnu.","language_code":"en"}')
  t1=$(date +%s.%N)
  echo "  run $i: HTTP $code  $(echo "$t1 - $t0" | bc)s  bytes=$(stat -c%s /tmp/c.out)"
done
