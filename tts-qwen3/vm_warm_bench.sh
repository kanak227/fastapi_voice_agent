#!/usr/bin/env bash
# Warm latency benchmark for MMS Hindi with prosody-via-silence.
set -u
t0=$(date +%s.%N)
curl -s -o /tmp/hi_warm.pcm -w "HTTP=%{http_code} bytes=%{size_download}\n" \
  -X POST http://localhost:8000/v1/text-to-speech/mms-hindi \
  -H "Content-Type: application/json" \
  -d '{"text":"एक, दो, तीन। चार, पाँच, छः। सात, आठ, नौ, दस।","language_code":"hi"}'
t1=$(date +%s.%N)
echo "warm_synth_time=$(echo "$t1-$t0" | bc)s"
