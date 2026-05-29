#!/usr/bin/env bash
echo "=== package check inside container ==="
sudo docker exec qwen3-tts python -c "import uroman; print('uroman OK', getattr(uroman,'__version__','?'))" 2>&1
sudo docker exec qwen3-tts python -c "import indic_transliteration; print('indic_transliteration OK')" 2>&1
