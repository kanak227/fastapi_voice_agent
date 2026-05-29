import inspect
import qwen_tts
from qwen_tts import Qwen3TTSModel

print("=== Qwen3TTSModel public methods ===")
print([x for x in dir(Qwen3TTSModel) if not x.startswith("_")])

print("\n=== generate_custom_voice signature ===")
try:
    print(inspect.signature(Qwen3TTSModel.generate_custom_voice))
except Exception as e:
    print("sig err:", e)

# Look for speaker/embedding related methods
print("\n=== speaker/embedding related ===")
for x in dir(Qwen3TTSModel):
    if any(k in x.lower() for k in ("speaker", "embed", "voice", "prepare", "encode", "cache")):
        print(" ", x)
