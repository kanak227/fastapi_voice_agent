"""Benchmark generate_custom_voice in streaming vs non-streaming mode on the VM GPU."""
import time
import torch
from qwen_tts import Qwen3TTSModel

MODEL_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
print("loading model (fp32)...")
m = Qwen3TTSModel.from_pretrained(MODEL_ID, device_map="cuda", torch_dtype=torch.float32)

SHORT = "Krishna is a Hindu deity."
LONG = "Krishna is a principal deity in Hinduism. He is revered as the eighth avatar of Vishnu."

def run(label, text, **kw):
    # warm
    try:
        m.generate_custom_voice(text=text, speaker="serena", language="english", **kw)
    except Exception as e:
        print(f"{label}: warm err {type(e).__name__}: {e}")
        return
    times = []
    for _ in range(3):
        t0 = time.time()
        wavs, sr = m.generate_custom_voice(text=text, speaker="serena", language="english", **kw)
        torch.cuda.synchronize()
        times.append(time.time() - t0)
    n = sum(len(w) for w in wavs) if wavs else 0
    print(f"{label}: avg={sum(times)/len(times):.2f}s  runs={[f'{t:.2f}' for t in times]}  samples={n} sr={sr}")

print("\n--- non_streaming_mode=True (default) ---")
run("short non-stream", SHORT, non_streaming_mode=True)
run("long  non-stream", LONG, non_streaming_mode=True)

print("\n--- non_streaming_mode=False ---")
run("short stream", SHORT, non_streaming_mode=False)
run("long  stream", LONG, non_streaming_mode=False)
