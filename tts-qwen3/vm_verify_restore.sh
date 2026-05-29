#!/usr/bin/env bash
set -u
echo "=== docker ps ==="
sudo docker ps --format '{{.Names}} {{.Status}}'
echo "=== health ==="
curl -s http://localhost:8000/health | grep -o '"status":"[^"]*"\|"dtype":"[^"]*"'
echo
echo "=== synth test ==="
curl -s -X POST http://localhost:8000/v1/text-to-speech/serena \
  -H 'Content-Type: application/json' \
  -d '{"text":"Krishna is a Hindu deity.","language_code":"en"}' \
  -o /tmp/t.out -w 'HTTP %{http_code} size=%{size_download}\n'
