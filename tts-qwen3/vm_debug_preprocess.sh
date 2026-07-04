#!/usr/bin/env bash
# Debug: see what text FastPitch actually receives after preprocessing
set -u

echo "=== Add debug logging to see preprocessed text ==="
sudo docker exec qwen3-tts python3 -c '
import sys
sys.path.insert(0, "/app")
from server import _preprocess_for_fastpitch

tests = [
    "यह एक test है। आपका phone number क्या है?",
    "### शुल्क ₹250 है और 18% छूट मिलेगी।",
    "Krishna एक deity हैं। उन्हें Vishnu का avatar माना जाता है।",
    "AI और technology का उपयोग करें। Digital literacy important है।",
    "sustainability और entrepreneurship सीखें।",
    "नमस्ते, आप कैसे हैं? मैं ठीक हूँ। धन्यवाद!",
]

for t in tests:
    result = _preprocess_for_fastpitch(t, "hi")
    print(f"IN:  {t}")
    print(f"OUT: {result}")
    print()
'
