#!/usr/bin/env bash
# Verify request-superseding on the PROD container (:8000): fire a long request
# A, then a newer request B ~1s later. A should be superseded (409), B succeeds.
set -u
echo "=== overlapping requests on prod :8000 ==="
LONG="Krishna is a principal deity in Hinduism. He is revered as the eighth avatar of Vishnu. He delivered the teachings of the Bhagavad Gita to Arjuna on the battlefield of Kurukshetra, guiding him through doubt and despair."

curl -s -o /tmp/A.out -w "A_HTTP=%{http_code} A_bytes=%{size_download}\n" \
  -X POST http://localhost:8000/v1/text-to-speech/serena \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"$LONG\",\"language_code\":\"english\"}" &
APID=$!
sleep 1
curl -s -o /tmp/B.out -w "B_HTTP=%{http_code} B_bytes=%{size_download}\n" \
  -X POST http://localhost:8000/v1/text-to-speech/serena \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"Hello there.\",\"language_code\":\"english\"}"
wait $APID

echo "=== MMS Hindi still works ==="
curl -s -o /tmp/H.out -w "H_HTTP=%{http_code} H_bytes=%{size_download}\n" \
  -X POST http://localhost:8000/v1/text-to-speech/mms-hindi \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"नमस्ते, यह एक परीक्षण है।\",\"language_code\":\"hi\"}"
