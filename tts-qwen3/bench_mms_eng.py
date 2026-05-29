"""Check MMS English availability + speed vs Qwen on the T4."""
import time
import torch
from transformers import VitsModel, AutoTokenizer

DEVICE = "cuda"
name = "facebook/mms-tts-eng"
print(f"loading {name} ...")
t0 = time.time()
tok = AutoTokenizer.from_pretrained(name)
model = VitsModel.from_pretrained(name).to(DEVICE).eval()
print(f"loaded in {time.time()-t0:.1f}s")

def run(label, text):
    inp = tok(text, return_tensors="pt").to(DEVICE)
    # warm
    with torch.no_grad():
        model(**inp).waveform
    torch.cuda.synchronize()
    times = []
    for _ in range(3):
        t0 = time.time()
        with torch.no_grad():
            wav = model(**inp).waveform
        torch.cuda.synchronize()
        times.append(time.time() - t0)
    n = wav.shape[-1]
    sr = model.config.sampling_rate
    print(f"{label}: avg={sum(times)/len(times):.3f}s  audio={n/sr:.2f}s  ratio={(sum(times)/len(times))/(n/sr):.2f}x")

run("short", "Krishna is a Hindu deity.")
run("long", "Krishna is a principal deity in Hinduism. He is revered as the eighth avatar of Vishnu.")
