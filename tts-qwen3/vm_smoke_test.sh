#!/usr/bin/env bash
# Smoke test for the Qwen3 + MMS TTS service running on this VM.
set -u
BASE="http://localhost:8000"

echo "=== /health ==="
curl -s "$BASE/health"; echo

echo "=== /v1/voices (all) ==="
curl -s "$BASE/v1/voices" | head -c 400; echo

echo "=== serena (en) ==="
curl -s -X POST "$BASE/v1/text-to-speech/serena" \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hello, this is a voice selection test.","language_code":"en"}' \
  -o /tmp/serena.mp3 -D /tmp/serena.hdr -w 'HTTP %{http_code} size=%{size_download}\n'
grep -i 'x-voice-id\|x-engine\|x-language' /tmp/serena.hdr

echo "=== ryan (en) ==="
curl -s -X POST "$BASE/v1/text-to-speech/ryan" \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hello, this is a voice selection test.","language_code":"en"}' \
  -o /tmp/ethan.mp3 -D /tmp/ethan.hdr -w 'HTTP %{http_code} size=%{size_download}\n'
grep -i 'x-voice-id\|x-engine\|x-language' /tmp/ethan.hdr

echo "=== voice-selection check (serena vs ryan must differ) ==="
S=$(md5sum /tmp/serena.mp3 | cut -d' ' -f1)
E=$(md5sum /tmp/ethan.mp3 | cut -d' ' -f1)
echo "serena md5=$S"
echo "ethan  md5=$E"
if [ "$S" != "$E" ] && [ -s /tmp/serena.mp3 ] && [ -s /tmp/ethan.mp3 ]; then
  # Both must be real audio (HTTP 200), not error JSON. Check the http codes captured above.
  if head -c 4 /tmp/serena.mp3 | grep -q "{" || head -c 4 /tmp/ethan.mp3 | grep -q "{"; then
    echo "FAIL: one of the voices returned an error JSON, not audio"
  else
    echo "PASS: voices produce different audio"
  fi
else
  echo "FAIL: voices identical or empty"
fi

echo "=== hindi MMS (hi) ==="
curl -s -X POST "$BASE/v1/text-to-speech/mms-hindi" \
  -H 'Content-Type: application/json' \
  -d '{"text":"नमस्ते, यह एक परीक्षण है।","language_code":"hi"}' \
  -o /tmp/hi.mp3 -D /tmp/hi.hdr -w 'HTTP %{http_code} size=%{size_download}\n'
grep -i 'x-engine\|x-language' /tmp/hi.hdr

echo "=== tamil MMS (ta) ==="
curl -s -X POST "$BASE/v1/text-to-speech/mms-tamil" \
  -H 'Content-Type: application/json' \
  -d '{"text":"வணக்கம், இது ஒரு சோதனை.","language_code":"ta"}' \
  -o /tmp/ta.mp3 -D /tmp/ta.hdr -w 'HTTP %{http_code} size=%{size_download}\n'
grep -i 'x-engine\|x-language' /tmp/ta.hdr

echo "=== hinglish (hi-Latn) -> should produce audio or clear 500 ==="
curl -s -X POST "$BASE/v1/text-to-speech/mms-hindi" \
  -H 'Content-Type: application/json' \
  -d '{"text":"namaste, aap kaise hain?","language_code":"hi-Latn"}' \
  -o /tmp/hil.out -w 'HTTP %{http_code} size=%{size_download}\n'
head -c 200 /tmp/hil.out; echo

echo "=== urdu (ur) -> should produce audio or clear 500 ==="
curl -s -X POST "$BASE/v1/text-to-speech/mms-urdu" \
  -H 'Content-Type: application/json' \
  -d '{"text":"سلام، یہ ایک ٹیسٹ ہے۔","language_code":"ur"}' \
  -o /tmp/ur.out -w 'HTTP %{http_code} size=%{size_download}\n'
head -c 200 /tmp/ur.out; echo

echo "=== DONE ==="
