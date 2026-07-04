#!/usr/bin/env bash
set -u

echo "=== Test real chatbot content ==="
sudo docker exec qwen3-tts python3 -c '
import sys
sys.path.insert(0, "/app")
from server import _preprocess_for_fastpitch

text = "नमस्ते! 👋 मैं SmartE हूँ, आपका CBSE शिक्षा सलाहकार। 📚  आप CBSE शिक्षा से संबंधित किस विषय पर जानकारी चाहते हैं या आपका क्या प्रश्न है? 💡 कृपया अपना प्रश्न स्पष्ट करें ताकि मैं आपकी बेहतर मदद कर सकूँ।  मैं यहाँ आपकी सहायता के लिए हूँ! ✨"

print("IN:", text)
print()
result = _preprocess_for_fastpitch(text, "hi")
print("OUT:", result)
print()
print("LEN:", len(result), "chars")

# Check for any non-Devanagari, non-punct chars remaining
import unicodedata
bad = []
for c in result:
    if c in " !,-.;:?\x27":
        continue
    name = unicodedata.name(c, "UNKNOWN")
    if "DEVANAGARI" not in name and c not in "\n":
        bad.append((c, name))
if bad:
    print("WARNING - non-Devanagari chars remaining:")
    for c, name in bad[:10]:
        print(f"  {repr(c)} = {name}")
else:
    print("CLEAN: all chars are Devanagari + supported punctuation")
'

echo ""
echo "=== Synthesize it ==="
t0=$(date +%s.%N)
HTTP=$(curl -s -o /tmp/real_test.pcm -w "%{http_code}" \
  -X POST http://localhost:8000/v1/text-to-speech/indic-hindi-female \
  -H "Content-Type: application/json" \
  -d '{"text":"नमस्ते! 👋 मैं SmartE हूँ, आपका CBSE शिक्षा सलाहकार। 📚  आप CBSE शिक्षा से संबंधित किस विषय पर जानकारी चाहते हैं या आपका क्या प्रश्न है? 💡 कृपया अपना प्रश्न स्पष्ट करें ताकि मैं आपकी बेहतर मदद कर सकूँ।  मैं यहाँ आपकी सहायता के लिए हूँ! ✨","language_code":"hi"}')
t1=$(date +%s.%N)
SIZE=$(stat -c%s /tmp/real_test.pcm)
echo "HTTP=$HTTP bytes=$SIZE time=$(echo "$t1-$t0" | bc)s"

echo ""
echo "=== Check logs for warnings ==="
sudo docker logs --tail 5 qwen3-tts 2>&1 | grep -v "GET /health"
