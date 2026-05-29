#!/usr/bin/env bash
# End-to-end test against the deployed Cloud Run backend.
set -u
BASE="https://multi-bot-server-650841589964.us-central1.run.app"

echo "=== backend health ==="
curl -s "$BASE/health" -w '\nHTTP %{http_code}\n' | tail -c 400; echo

echo "=== qwen voices (no filter) ==="
curl -s "$BASE/voice/voices?tts_provider=qwen" -w '\nHTTP %{http_code}\n' | head -c 800; echo

echo "=== qwen voices filtered: hi ==="
curl -s "$BASE/voice/voices?tts_provider=qwen&language=hi" -w '\nHTTP %{http_code}\n' | head -c 600; echo

echo "=== qwen voices filtered: en ==="
curl -s "$BASE/voice/voices?tts_provider=qwen&language=en" -w '\nHTTP %{http_code}\n' | head -c 600; echo

echo "=== DONE ==="
