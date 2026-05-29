#!/usr/bin/env bash
# Validate faster-qwen3-tts on the T4 INSIDE the running container's env
# (torch + CUDA already present). Installs into the container, then benchmarks
# CustomVoice TTFA + RTF with CUDA graphs.
set -u

echo "=== container torch / CUDA ==="
sudo docker exec qwen3-tts python -c "import torch; print('torch', torch.__version__, 'cuda', torch.version.cuda, 'is_avail', torch.cuda.is_available(), torch.cuda.get_device_name(0))"

echo
echo "=== pip install faster-qwen3-tts (into container) ==="
sudo docker exec qwen3-tts pip install --no-cache-dir faster-qwen3-tts 2>&1 | tail -8

echo
echo "=== writing bench script into container ==="
sudo docker exec qwen3-tts bash -c 'cat > /tmp/fbench.py << "PYEOF"
import time, torch
from faster_qwen3_tts import FasterQwen3TTS

print("loading FasterQwen3TTS CustomVoice 0.6B ...")
t0=time.time()
m = FasterQwen3TTS.from_pretrained("Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice")
print(f"loaded in {time.time()-t0:.1f}s")

def bench_nonstream(text):
    # warm
    try:
        m.generate_custom_voice(text=text, language="English", speaker="serena")
    except Exception as e:
        print("warm err:", type(e).__name__, e); return
    ts=[]
    for _ in range(3):
        t0=time.time()
        audio,sr = m.generate_custom_voice(text=text, language="English", speaker="serena")
        torch.cuda.synchronize()
        ts.append(time.time()-t0)
    n = sum(len(a) for a in audio) if isinstance(audio,list) else len(audio)
    secs = n/sr
    print(f"  NONSTREAM avg={sum(ts)/len(ts):.2f}s audio={secs:.2f}s RTF={secs/(sum(ts)/len(ts)):.2f}")

def bench_stream(text, chunk_size=8):
    # measure time-to-first-audio chunk
    for trial in range(2):
        t0=time.time()
        first=None; total_samples=0; sr=24000
        for audio_chunk, _sr, timing in m.generate_custom_voice_streaming(text=text, language="English", speaker="serena", chunk_size=chunk_size):
            if first is None:
                first=time.time()-t0
            sr=_sr
            total_samples += len(audio_chunk)
        dur=time.time()-t0
        secs=total_samples/sr
        print(f"  STREAM trial{trial}: TTFA={first*1000:.0f}ms total={dur:.2f}s audio={secs:.2f}s RTF={secs/dur:.2f}")

print("\n--- short ---")
bench_nonstream("Krishna is the eighth avatar of Vishnu.")
bench_stream("Krishna is the eighth avatar of Vishnu.", chunk_size=8)
print("\n--- long ---")
bench_nonstream("Krishna is a principal deity in Hinduism. He is revered as the eighth avatar of Vishnu. He delivered the teachings of the Bhagavad Gita to Arjuna.")
bench_stream("Krishna is a principal deity in Hinduism. He is revered as the eighth avatar of Vishnu. He delivered the teachings of the Bhagavad Gita to Arjuna.", chunk_size=8)
PYEOF'

echo
echo "=== running benchmark ==="
sudo docker exec qwen3-tts python /tmp/fbench.py 2>&1 | grep -v "Setting \`pad_token" | tail -40
