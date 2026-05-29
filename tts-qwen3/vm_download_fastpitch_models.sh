#!/usr/bin/env bash
# Download AI4Bharat FastPitch + HiFiGAN models to the persistent volume.
# Run this ONCE on the VM. Models persist across container recreates.
set -eu
DEST="/var/lib/qwen-models/fastpitch"
mkdir -p "$DEST"

for lang in hi ta te mr bn gu kn ml pa; do
  if [ -f "$DEST/$lang/fastpitch/best_model.pth" ]; then
    echo "$lang: already downloaded"
    continue
  fi
  echo "$lang: downloading..."
  curl -sL "https://github.com/AI4Bharat/Indic-TTS/releases/download/v1-checkpoints-release/${lang}.zip" -o "/tmp/${lang}.zip"
  unzip -q "/tmp/${lang}.zip" -d "$DEST/"
  rm "/tmp/${lang}.zip"
  echo "$lang: done"
done

echo "=== Models on disk ==="
du -sh "$DEST"/*
