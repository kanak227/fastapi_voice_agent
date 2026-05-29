#!/usr/bin/env bash
# Probe what the MMS Hindi tokenizer does with punctuation: does it keep
# commas/periods/danda (which create pauses) or silently drop them?
set -u
sudo docker exec qwen3-tts python - << 'PYEOF'
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("facebook/mms-tts-hin")
print("vocab size:", tok.vocab_size)
vocab = tok.get_vocab()
# Which punctuation chars exist in the vocab at all?
for ch in [",", ".", "?", "!", ";", ":", "-", "।", " "]:
    print(repr(ch), "in vocab:", ch in vocab)

samples = [
    "नमस्ते, यह एक परीक्षण है।",
    "रुको. अब बोलो.",
    "एक, दो, तीन।",
]
print("--- tokenization (normalized text the model actually sees) ---")
for s in samples:
    enc = tok(s, return_tensors="pt")
    ids = enc["input_ids"][0].tolist()
    decoded = tok.decode(ids)
    print("IN :", s)
    print("DEC:", repr(decoded))
    print("ntok:", len(ids))
    print()

# English MMS for comparison (does Qwen handle it differently? MMS not used for en,
# but show whether comma survives in any VITS tokenizer)
PYEOF
