# -*- coding: utf-8 -*-
"""Probe how the MMS Hindi VITS tokenizer treats punctuation."""
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained("facebook/mms-tts-hin")
print("vocab size:", tok.vocab_size)
vocab = tok.get_vocab()
for ch in [",", ".", "?", "!", ";", ":", "-", "\u0964", " "]:
    print(repr(ch), "in vocab:", ch in vocab)

samples = [
    "\u0928\u092e\u0938\u094d\u0924\u0947, \u092f\u0939 \u090f\u0915 \u092a\u0930\u0940\u0915\u094d\u0937\u0923 \u0939\u0948\u0964",
    "\u090f\u0915, \u0926\u094b, \u0924\u0940\u0928\u0964",
]
print("--- tokenization (what the model actually sees) ---")
for s in samples:
    enc = tok(s, return_tensors="pt")
    ids = enc["input_ids"][0].tolist()
    decoded = tok.decode(ids)
    print("IN :", s)
    print("DEC:", repr(decoded))
    print("ntok:", len(ids))
    print()
