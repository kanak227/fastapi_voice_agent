"""Probe which MMS-TTS models exist + work for the Qwen-only languages."""
import time
import torch
from transformers import VitsModel, AutoTokenizer

DEVICE = "cuda"
candidates = {
    "en": ["eng"],
    "fr": ["fra"],
    "de": ["deu"],
    "es": ["spa"],
    "zh": ["cmn-script_simplified", "cmn", "zho"],
    "ja": ["jpn"],
    "ru": ["rus"],
    "it": ["ita"],
    "pt": ["por"],
    "ko": ["kor"],
}
samples = {
    "en": "Hello, this is a test.",
    "fr": "Bonjour, ceci est un test.",
    "de": "Hallo, das ist ein Test.",
    "es": "Hola, esto es una prueba.",
    "zh": "你好，这是一个测试。",
    "ja": "こんにちは、これはテストです。",
    "ru": "Привет, это тест.",
    "it": "Ciao, questo è un test.",
    "pt": "Olá, isto é um teste.",
    "ko": "안녕하세요, 이것은 테스트입니다.",
}

for lang, codes in candidates.items():
    found = None
    for code in codes:
        name = f"facebook/mms-tts-{code}"
        try:
            tok = AutoTokenizer.from_pretrained(name)
            model = VitsModel.from_pretrained(name).to(DEVICE).eval()
            inp = tok(samples[lang], return_tensors="pt").to(DEVICE)
            t0 = time.time()
            with torch.no_grad():
                wav = model(**inp).waveform
            torch.cuda.synchronize()
            dt = time.time() - t0
            sr = model.config.sampling_rate
            secs = wav.shape[-1] / sr
            print(f"{lang}: {code} OK  {dt:.2f}s  audio={secs:.2f}s  ratio={dt/max(secs,0.01):.2f}x")
            found = code
            del model
            torch.cuda.empty_cache()
            break
        except Exception as e:
            print(f"{lang}: {code} FAIL {type(e).__name__}: {str(e)[:80]}")
    if not found:
        print(f"{lang}: NO MMS MODEL")
