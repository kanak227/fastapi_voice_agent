#!/usr/bin/env bash
sudo docker exec qwen3-tts python3 -c '
import json, unicodedata
cfg = json.load(open("/models/fastpitch/hi/fastpitch/config.json"))
chars = cfg["characters"]["characters"]
print("Total chars in vocab:", len(chars))
print()
# Categorize
devanagari = [c for c in chars if "DEVANAGARI" in unicodedata.name(c, "")]
latin = [c for c in chars if "LATIN" in unicodedata.name(c, "")]
digits = [c for c in chars if c.isdigit()]
punct = [c for c in chars if unicodedata.category(c).startswith("P") or c in " !,-.;:?"]
other = [c for c in chars if c not in devanagari and c not in latin and c not in digits and c not in punct]
print(f"Devanagari: {len(devanagari)} chars")
print(f"Latin: {len(latin)} -> {repr(latin)}")
print(f"Digits: {len(digits)} -> {repr(digits)}")
print(f"Punctuation: {repr(punct)}")
print(f"Other: {repr(other)}")
print()
# Test: what happens with English words?
print("=== Test: English in Hindi text ===")
from TTS.utils.synthesizer import Synthesizer
synth = Synthesizer(
    tts_checkpoint="/models/fastpitch/hi/fastpitch/best_model.pth",
    tts_config_path="/models/fastpitch/hi/fastpitch/config.json",
    vocoder_checkpoint="/models/fastpitch/hi/hifigan/best_model.pth",
    vocoder_config="/models/fastpitch/hi/hifigan/config.json",
    use_cuda=False,
)
import numpy as np
# Pure Hindi
wav1 = synth.tts("नमस्ते, आप कैसे हैं.", speaker_name="female")
print(f"Pure Hindi: {len(wav1)} samples = {len(wav1)/22050:.2f}s")
# Hindi with English word
wav2 = synth.tts("यह एक test है.", speaker_name="female")
print(f"Hindi+English: {len(wav2)} samples = {len(wav2)/22050:.2f}s")
# Hindi with number (digit)
wav3 = synth.tts("कीमत 250 रुपये है.", speaker_name="female")
print(f"Hindi+digits: {len(wav3)} samples = {len(wav3)/22050:.2f}s")
'
