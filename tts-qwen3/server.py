"""ElevenLabs-compatible multi-engine TTS service.

Routes each request to the best engine for the requested language:

* **Qwen3-TTS-12Hz-0.6B-CustomVoice** — high-quality custom-voice model.
  Native support: English, Chinese, French, German, Italian, Japanese,
  Korean, Portuguese, Russian, Spanish.
* **Meta MMS-TTS** (facebook/mms-tts-*) — covers everything else, including
  all the Indian regional languages our dashboards expose
  (Hindi, Tamil, Telugu, Marathi, Bengali, Gujarati, Kannada, Malayalam,
  Punjabi, Urdu) plus Arabic and many more. Models are lazy-loaded per
  language so memory stays small.

The HTTP shape mirrors ElevenLabs so the existing FastAPI provider can
talk to this service unchanged. Just point ``ELEVENLABS_BASE_URL`` here.

Endpoints
---------
GET  /health
GET  /v1/voices
POST /v1/text-to-speech/{voice_id}
"""

from __future__ import annotations

import io
import logging
import os
import random
import re
import threading
from typing import Optional

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, Header, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field
from faster_qwen3_tts import FasterQwen3TTS


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
QWEN_MODEL_ID = os.getenv("QWEN_MODEL_ID", "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice")
DEVICE = os.getenv("QWEN_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
DTYPE_STR = os.getenv("QWEN_DTYPE", "float32").lower()
DEFAULT_VOICE_ID = os.getenv("QWEN_DEFAULT_VOICE_ID", "serena")
DEFAULT_LANGUAGE = os.getenv("QWEN_DEFAULT_LANGUAGE", "english")
SEED = int(os.getenv("QWEN_SEED", "1234"))
API_KEY = os.getenv("TTS_API_KEY", "")  # optional, blank = no auth

# Streaming chunk size for FasterQwen3TTS. 8 steps ≈ 667ms of audio per chunk
# at 12Hz. The faster runtime emits the first chunk in ~680ms on a T4 (vs
# 6-40s for the old qwen-tts package), so even non-streaming HTTP responses
# are assembled from these fast streamed chunks.
QWEN_CHUNK_SIZE = int(os.getenv("QWEN_CHUNK_SIZE", "8"))

DTYPE_MAP = {
    "float16": torch.float16,
    "float32": torch.float32,
    "bfloat16": torch.bfloat16,
}
TORCH_DTYPE = DTYPE_MAP.get(DTYPE_STR, torch.float32)


# ---- Engine routing -------------------------------------------------------
# Languages supported natively by Qwen3-TTS-12Hz-0.6B-CustomVoice.
QWEN_SUPPORTED_LANGS = {
    "english", "chinese", "french", "german", "italian",
    "japanese", "korean", "portuguese", "russian", "spanish",
}

# Map BCP-47 / two-letter codes to a Qwen language label.
QWEN_LANG_MAP: dict[str, str] = {
    "en": "english",
    "fr": "french",
    "de": "german",
    "es": "spanish",
    "it": "italian",
    "pt": "portuguese",
    "ru": "russian",
    "ja": "japanese",
    "ko": "korean",
    "zh": "chinese",
}

# Map BCP-47 codes to Meta MMS-TTS ISO 639-3 model suffixes.
# https://huggingface.co/facebook/mms-tts-{code}
# NOTE: MMS is now only used as a FALLBACK for languages not covered by
# AI4Bharat FastPitch (Urdu, Arabic). For the 13 Indian languages that
# FastPitch supports, it is preferred due to much better quality and speed.
MMS_LANG_MAP: dict[str, str] = {
    "ur": "urd-script_arabic",  # Urdu MMS ships only as the Arabic-script checkpoint
    "ar": "ara",
}

# AI4Bharat FastPitch + HiFiGAN: high-quality, fully-parallel TTS for 13
# Indian languages. Trained on IndicTTS dataset (studio recordings, male +
# female speakers). Published at ICASSP 2023, SOTA for all 13 languages.
# Models downloaded from: https://github.com/AI4Bharat/Indic-TTS/releases/tag/v1-checkpoints-release
FASTPITCH_LANG_MAP: dict[str, str] = {
    "hi": "hi",
    "hi-latn": "hi",  # Hinglish -> Hindi voice (text is transliterated upstream)
    "ta": "ta",
    "te": "te",
    "mr": "mr",
    "bn": "bn",
    "gu": "gu",
    "kn": "kn",
    "ml": "ml",
    "pa": "pa",
    "as": "as",  # Assamese
    "or": "or",  # Odia
    "raj": "raj",  # Rajasthani
}

# Base directory where FastPitch checkpoints are stored (per-language subdirs).
FASTPITCH_MODELS_DIR = os.getenv("FASTPITCH_MODELS_DIR", "/models/fastpitch")


# Voice catalog. The voice_id is what the chatbot sends in the URL path.
VOICE_CATALOG: list[dict] = [
    # Qwen3-TTS voices (English + CJK + European)
    {"voice_id": "serena", "name": "Serena", "labels": {"gender": "female", "accent": "neutral"}, "languages": ["en", "fr", "de", "es", "it", "pt", "ru", "ja", "ko", "zh"]},
    {"voice_id": "vivian", "name": "Vivian", "labels": {"gender": "female", "accent": "neutral"}, "languages": ["en", "fr", "de", "es", "it", "pt", "ru", "ja", "ko", "zh"]},
    {"voice_id": "ryan", "name": "Ryan", "labels": {"gender": "male", "accent": "neutral"}, "languages": ["en", "fr", "de", "es", "it", "pt", "ru", "ja", "ko", "zh"]},
    {"voice_id": "aiden", "name": "Aiden", "labels": {"gender": "male", "accent": "neutral"}, "languages": ["en", "fr", "de", "es", "it", "pt", "ru", "ja", "ko", "zh"]},
    {"voice_id": "eric", "name": "Eric", "labels": {"gender": "male", "accent": "neutral"}, "languages": ["en", "fr", "de", "es", "it", "pt", "ru", "ja", "ko", "zh"]},
    {"voice_id": "dylan", "name": "Dylan", "labels": {"gender": "male", "accent": "neutral"}, "languages": ["en", "fr", "de", "es", "it", "pt", "ru", "ja", "ko", "zh"]},
    # AI4Bharat FastPitch voices (Indian languages — male + female per language)
    {"voice_id": "indic-hindi-female", "name": "Hindi Female", "labels": {"gender": "female", "accent": "hindi"}, "languages": ["hi", "hi-Latn"]},
    {"voice_id": "indic-hindi-male", "name": "Hindi Male", "labels": {"gender": "male", "accent": "hindi"}, "languages": ["hi", "hi-Latn"]},
    {"voice_id": "indic-tamil-female", "name": "Tamil Female", "labels": {"gender": "female", "accent": "tamil"}, "languages": ["ta"]},
    {"voice_id": "indic-tamil-male", "name": "Tamil Male", "labels": {"gender": "male", "accent": "tamil"}, "languages": ["ta"]},
    {"voice_id": "indic-telugu-female", "name": "Telugu Female", "labels": {"gender": "female", "accent": "telugu"}, "languages": ["te"]},
    {"voice_id": "indic-telugu-male", "name": "Telugu Male", "labels": {"gender": "male", "accent": "telugu"}, "languages": ["te"]},
    {"voice_id": "indic-marathi-female", "name": "Marathi Female", "labels": {"gender": "female", "accent": "marathi"}, "languages": ["mr"]},
    {"voice_id": "indic-marathi-male", "name": "Marathi Male", "labels": {"gender": "male", "accent": "marathi"}, "languages": ["mr"]},
    {"voice_id": "indic-bengali-female", "name": "Bengali Female", "labels": {"gender": "female", "accent": "bengali"}, "languages": ["bn"]},
    {"voice_id": "indic-bengali-male", "name": "Bengali Male", "labels": {"gender": "male", "accent": "bengali"}, "languages": ["bn"]},
    {"voice_id": "indic-gujarati-female", "name": "Gujarati Female", "labels": {"gender": "female", "accent": "gujarati"}, "languages": ["gu"]},
    {"voice_id": "indic-gujarati-male", "name": "Gujarati Male", "labels": {"gender": "male", "accent": "gujarati"}, "languages": ["gu"]},
    {"voice_id": "indic-kannada-female", "name": "Kannada Female", "labels": {"gender": "female", "accent": "kannada"}, "languages": ["kn"]},
    {"voice_id": "indic-kannada-male", "name": "Kannada Male", "labels": {"gender": "male", "accent": "kannada"}, "languages": ["kn"]},
    {"voice_id": "indic-malayalam-female", "name": "Malayalam Female", "labels": {"gender": "female", "accent": "malayalam"}, "languages": ["ml"]},
    {"voice_id": "indic-malayalam-male", "name": "Malayalam Male", "labels": {"gender": "male", "accent": "malayalam"}, "languages": ["ml"]},
    {"voice_id": "indic-punjabi-female", "name": "Punjabi Female", "labels": {"gender": "female", "accent": "punjabi"}, "languages": ["pa"]},
    {"voice_id": "indic-punjabi-male", "name": "Punjabi Male", "labels": {"gender": "male", "accent": "punjabi"}, "languages": ["pa"]},
    # MMS fallback voices (Urdu, Arabic — not covered by FastPitch)
    {"voice_id": "mms-urdu", "name": "Urdu (MMS)", "labels": {"gender": "neutral", "accent": "urdu"}, "languages": ["ur"]},
    {"voice_id": "mms-arabic", "name": "Arabic (MMS)", "labels": {"gender": "neutral", "accent": "arabic"}, "languages": ["ar"]},
]

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("qwen-tts-service")


# ---------------------------------------------------------------------------
# Schemas (subset of ElevenLabs request shape)
# ---------------------------------------------------------------------------
class VoiceSettings(BaseModel):
    stability: Optional[float] = None
    similarity_boost: Optional[float] = None
    style: Optional[float] = None
    use_speaker_boost: Optional[bool] = None


class TTSRequestBody(BaseModel):
    text: str = Field(..., min_length=1)
    model_id: Optional[str] = None
    language_code: Optional[str] = None
    output_format: Optional[str] = None
    voice_settings: Optional[VoiceSettings] = None


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Multi-engine TTS (Qwen3 + MMS)", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ---------------------------------------------------------------------------
# Engine: Qwen3-TTS
# ---------------------------------------------------------------------------
@app.on_event("startup")
def _load_models() -> None:
    logger.info("Loading FasterQwen3TTS %s on %s (dtype=%s)", QWEN_MODEL_ID, DEVICE, DTYPE_STR)
    _set_seed(SEED)

    # Turing-era (T4) perf knobs: let cuDNN pick the fastest kernels and allow
    # TF32 on matmuls. These are global and safe for inference.
    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = True
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True

    # FasterQwen3TTS captures CUDA graphs for the talker + code-predictor on
    # first use, collapsing ~500 tiny kernel launches per decode step into one
    # replayed graph. This is what makes the T4 hit real-time (RTF ~1.0+,
    # ~680ms time-to-first-audio) instead of the 6-40s the plain qwen-tts
    # package produced (GPU was idle waiting on Python between kernels).
    app.state.qwen_model = FasterQwen3TTS.from_pretrained(QWEN_MODEL_ID)
    app.state.qwen_lock = threading.Lock()
    # MMS models are lazy-loaded on first use to keep startup fast and
    # memory low when only some languages are actually used.
    app.state.mms_cache: dict[str, tuple] = {}
    app.state.mms_lock = threading.Lock()
    app.state.uroman = None  # lazy-init
    # FastPitch models are also lazy-loaded per language.
    app.state.fastpitch_cache: dict[str, object] = {}
    app.state.fastpitch_lock = threading.Lock()
    app.state.graphs_warmed = False

    # ---- Request queue for concurrent handling --------------------------------
    # Instead of blocking with a lock, queue requests and process them in order.
    # Multiple users can submit requests; they wait in queue instead of blocking.
    from queue import Queue
    import asyncio
    
    app.state.request_queue = Queue(maxsize=100)  # Max 100 queued requests
    app.state.processing = False
    app.state.queue_lock = threading.Lock()
    
    # Request timeout: How long a request can wait in queue before being dropped
    app.state.queue_timeout_seconds = int(os.getenv("QUEUE_TIMEOUT_SECONDS", "30"))
    
    # Track active request for superseding
    app.state.current_request_seq = 0
    app.state.seq_lock = threading.Lock()
    
    # Simple in-memory cache for TTS responses (helps with repeated phrases)
    app.state.tts_cache: dict[str, tuple] = {}  # key -> (audio, sr, timestamp)
    app.state.cache_max_size = int(os.getenv("TTS_CACHE_SIZE", "100"))
    app.state.cache_ttl_seconds = int(os.getenv("TTS_CACHE_TTL", "3600"))  # 1 hour

    # Warm the CUDA graphs once so the first real request doesn't pay the
    # capture cost (~3-5s). Best-effort; failures fall back to lazy capture.
    try:
        with app.state.qwen_lock:
            for _chunk, _sr, _t in app.state.qwen_model.generate_custom_voice_streaming(
                text="Hello.", language="English", speaker=DEFAULT_VOICE_ID,
                chunk_size=QWEN_CHUNK_SIZE,
            ):
                pass
        app.state.graphs_warmed = True
        logger.info("FasterQwen3TTS CUDA graphs warmed.")
    except Exception as exc:  # pragma: no cover - warmup is best effort
        logger.warning("CUDA graph warmup skipped: %s", exc)

    logger.info("FasterQwen3TTS ready. MMS engines will load on demand.")

    # Pre-load FastPitch models for the most-used Indian languages so the
    # first real request doesn't pay the ~10s model-load cost.
    _PRELOAD_LANGS = os.getenv("FASTPITCH_PRELOAD", "hi,ta,te,bn,mr").split(",")
    for lang in _PRELOAD_LANGS:
        lang = lang.strip()
        if lang and lang in FASTPITCH_LANG_MAP:
            try:
                _get_fastpitch(lang, "female")
                logger.info("FastPitch %s preloaded.", lang)
            except Exception as exc:
                logger.warning("FastPitch %s preload failed (will lazy-load): %s", lang, exc)


class RequestSuperseded(Exception):
    """Raised when a newer TTS request arrives and this one should abort."""


class RequestTimeout(Exception):
    """Raised when a TTS request times out in queue."""


def _make_cache_key(text: str, engine: str, arg: str, voice: str) -> str:
    """Create cache key for TTS response."""
    import hashlib
    key_str = f"{engine}:{arg}:{voice}:{text}"
    return hashlib.md5(key_str.encode()).hexdigest()


def _get_cached_tts(cache_key: str):
    """Get cached TTS response if available and not expired."""
    import time
    if cache_key in app.state.tts_cache:
        audio, sr, timestamp = app.state.tts_cache[cache_key]
        if (time.time() - timestamp) < app.state.cache_ttl_seconds:
            logger.debug("Cache hit for key=%s", cache_key[:8])
            return audio, sr
        else:
            # Expired, remove it
            del app.state.tts_cache[cache_key]
    return None, None


def _cache_tts(cache_key: str, audio: np.ndarray, sr: int):
    """Cache TTS response."""
    import time
    # Simple LRU: if cache is full, remove oldest entry
    if len(app.state.tts_cache) >= app.state.cache_max_size:
        oldest_key = min(app.state.tts_cache.items(), key=lambda x: x[1][2])[0]
        del app.state.tts_cache[oldest_key]
    
    app.state.tts_cache[cache_key] = (audio.copy(), sr, time.time())
    logger.debug("Cached response for key=%s (cache_size=%d)", cache_key[:8], len(app.state.tts_cache))


def _claim_request() -> int:
    """Claim the current request slot."""
    with app.state.seq_lock:
        app.state.current_request_seq += 1
        return app.state.current_request_seq


def _finish_request(seq: int) -> None:
    """Finish request (placeholder for future cleanup)."""
    pass  # Currently no cleanup needed, but keeping for future use


def _is_current(my_seq: int) -> bool:
    """Check if this request is still the current one."""
    return my_seq >= app.state.current_request_seq


def _normalize_qwen_lang(language: str) -> str:
    """FasterQwen3TTS expects capitalized language names ('English')."""
    lang = (language or DEFAULT_LANGUAGE).strip()
    if lang and lang.lower() != "auto":
        return lang[:1].upper() + lang[1:]
    return DEFAULT_LANGUAGE[:1].upper() + DEFAULT_LANGUAGE[1:]


def _qwen_stream(text: str, language: str, speaker: str = None, my_seq: int | None = None):
    """Yield (audio_float32_mono, sample_rate) sub-chunks as the model renders.

    This is the realtime path: FasterQwen3TTS emits ~0.67s of audio every
    QWEN_CHUNK_SIZE steps (~680ms to first chunk on a T4), so the caller can
    forward audio to the browser while the rest is still being generated.

    If ``my_seq`` is provided, the loop aborts (raising RequestSuperseded) the
    moment a newer request has claimed a higher generation number — freeing the
    GPU lock for the new request instead of finishing stale audio.
    """
    speaker = speaker or DEFAULT_VOICE_ID
    lang = _normalize_qwen_lang(language)
    
    # Try to acquire lock with timeout instead of blocking forever
    acquired = app.state.qwen_lock.acquire(timeout=5.0)  # Wait max 5 seconds
    if not acquired:
        logger.warning("Failed to acquire GPU lock after 5s for seq=%d", my_seq or -1)
        raise HTTPException(status_code=503, detail="TTS service busy, try again")
    
    try:
        # If a newer request arrived while we waited for the lock, bail now.
        if my_seq is not None and not _is_current(my_seq):
            raise RequestSuperseded()
        
        with torch.inference_mode():
            for audio_chunk, chunk_sr, _timing in app.state.qwen_model.generate_custom_voice_streaming(
                text=text,
                language=lang,
                speaker=speaker,
                chunk_size=QWEN_CHUNK_SIZE,
            ):
                if my_seq is not None and not _is_current(my_seq):
                    # A newer request is waiting — stop generating and release
                    # the GPU lock so it can start immediately.
                    raise RequestSuperseded()
                arr = audio_chunk
                if hasattr(arr, "cpu"):
                    arr = arr.cpu().numpy()
                yield np.asarray(arr, dtype=np.float32).reshape(-1), int(chunk_sr or 24000)
    finally:
        app.state.qwen_lock.release()


def _qwen_synthesize(text: str, language: str, speaker: str = None, my_seq: int | None = None) -> tuple[np.ndarray, int]:
    """Synthesize a full clip by consuming the streaming generator.

    Used by the non-streaming endpoint. The streaming path underneath is what
    gives the low per-chunk latency (CUDA-graph replay).
    """
    chunks: list[np.ndarray] = []
    sr = 24000
    for arr, chunk_sr in _qwen_stream(text, language, speaker, my_seq=my_seq):
        sr = chunk_sr
        chunks.append(arr)

    if not chunks:
        raise RuntimeError("FasterQwen3TTS returned empty audio")
    audio = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]
    return np.asarray(audio, dtype=np.float32), int(sr)


# ---------------------------------------------------------------------------
# Engine: Meta MMS-TTS
# ---------------------------------------------------------------------------
def _romanize(text: str) -> str:
    """Romanize text via uroman (required by some MMS-TTS tokenizers).

    Raises HTTPException if uroman is not installed when called.
    """
    inst = app.state.uroman
    if inst is None:
        try:
            from uroman import Uroman
            inst = Uroman()
        except Exception:
            logger.critical("uroman package not installed — Urdu/script-based TTS will fail")
            inst = False
        app.state.uroman = inst
    if inst is False:
        raise HTTPException(
            status_code=500,
            detail="uroman package required for this language but not installed"
        )
    try:
        return inst.romanize_string(text)
    except Exception:
        return text


def _latn_to_devanagari(text: str) -> str:
    """Best-effort romanized Hindi → Devanagari for MMS-TTS Hindi.

    MMS Hindi tokenizer expects Devanagari; pure Latin "namaste" tokenizes
    to nothing. We use ITRANS/HK heuristics via indic-transliteration.
    
    Raises HTTPException if indic-transliteration is not installed.
    """
    try:
        from indic_transliteration.sanscript import transliterate, ITRANS, DEVANAGARI
        return transliterate(text, ITRANS, DEVANAGARI)
    except Exception:
        logger.critical("indic-transliteration package not installed — Hinglish TTS will fail")
        raise HTTPException(
            status_code=500,
            detail="indic-transliteration package required for Hinglish but not installed"
        )


def _get_mms(lang_iso639_3: str):
    cache: dict = app.state.mms_cache
    if lang_iso639_3 in cache:
        return cache[lang_iso639_3]

    with app.state.mms_lock:
        if lang_iso639_3 in cache:
            return cache[lang_iso639_3]

        from transformers import VitsModel, AutoTokenizer

        name = f"facebook/mms-tts-{lang_iso639_3}"
        logger.info("Loading MMS-TTS %s", name)
        tokenizer = AutoTokenizer.from_pretrained(name)
        model = VitsModel.from_pretrained(name)
        model = model.to(DEVICE)
        if TORCH_DTYPE != torch.float32 and DEVICE != "cpu":
            model = model.to(TORCH_DTYPE)
        model.eval()

        # Detect whether this language's tokenizer expects romanized input.
        # transformers stores it on the tokenizer or in init_kwargs.
        is_uroman = bool(
            getattr(tokenizer, "is_uroman", False)
            or tokenizer.init_kwargs.get("is_uroman", False)
        )

        cache[lang_iso639_3] = (model, tokenizer, is_uroman, threading.Lock())
        return cache[lang_iso639_3]


# ---------------------------------------------------------------------------
# MMS prosody: the VITS tokenizer drops ALL punctuation (comma, period, danda,
# question mark — none are in the 72-char vocab). So we split the input text
# at clause/sentence boundaries, synthesize each phrase independently, and
# stitch them together with silence gaps. This gives natural pauses that the
# engine itself cannot produce.
# ---------------------------------------------------------------------------
# Sentence-ending punctuation (period, danda, question, exclamation).
_MMS_SENTENCE_SPLIT = re.compile(r"(?<=[.!?\u0964\u0965])\s*")
# Clause-level punctuation (comma, semicolon, colon, em-dash).
_MMS_CLAUSE_SPLIT = re.compile(r"(?<=[,;:\u2014])\s*")

# Silence durations in seconds (tuned for natural Hindi speech rhythm).
_MMS_SENTENCE_PAUSE = 0.45   # ~450ms between sentences
_MMS_CLAUSE_PAUSE = 0.20     # ~200ms at commas/semicolons


def _mms_synthesize(text: str, lang_iso639_3: str, my_seq: int | None = None) -> tuple[np.ndarray, int]:
    """Synthesize text via MMS-TTS with injected silence for prosody.

    Because the MMS VITS tokenizer has no punctuation in its vocabulary,
    commas/periods/dandas are silently dropped and the output is one
    continuous monotone stream. We fix this by:
    1. Splitting text at sentence boundaries → synthesize each separately
    2. Splitting long sentences at clause boundaries (commas)
    3. Inserting silence gaps between the resulting audio segments
    """
    model, tokenizer, is_uroman, _per_lang_lock = _get_mms(lang_iso639_3)
    sr = int(model.config.sampling_rate)

    # Split into sentences first, then clauses within each sentence.
    sentences = [s.strip() for s in _MMS_SENTENCE_SPLIT.split(text) if s.strip()]
    if not sentences:
        sentences = [text.strip()]

    segments: list[tuple[str, float]] = []  # (phrase_text, pause_after)
    for sent in sentences:
        # Only split at clause boundaries if the sentence is long enough
        # to benefit from internal pauses (>6 words). Short sentences like
        # "एक, दो, तीन।" sound better synthesized as one unit.
        words_in_sent = len(sent.split())
        if words_in_sent > 6:
            clauses = [c.strip() for c in _MMS_CLAUSE_SPLIT.split(sent) if c.strip()]
        else:
            clauses = [sent]
        if not clauses:
            clauses = [sent]
        for i, clause in enumerate(clauses):
            if i == len(clauses) - 1:
                segments.append((clause, _MMS_SENTENCE_PAUSE))
            else:
                segments.append((clause, _MMS_CLAUSE_PAUSE))

    # Synthesize all segments under a SINGLE GPU lock acquisition to avoid
    # repeated lock contention and maximize throughput.
    audio_parts: list[np.ndarray] = []

    # Pre-tokenize all segments outside the lock (CPU work).
    tokenized_segments: list[tuple[dict | None, float]] = []
    for phrase, pause_sec in segments:
        clean = re.sub(r"[,.;:!?\u0964\u0965\u2014\u2013\u2026\"'\-]", "", phrase).strip()
        if not clean:
            tokenized_segments.append((None, pause_sec))
            continue
        input_text = _romanize(clean) if is_uroman else clean
        inputs = tokenizer(input_text, return_tensors="pt").to(DEVICE)
        if inputs["input_ids"].shape[-1] <= 2:
            tokenized_segments.append((None, pause_sec))
        else:
            tokenized_segments.append((inputs, pause_sec))

    # Single GPU lock for all segments.
    with app.state.qwen_lock:
        if my_seq is not None and not _is_current(my_seq):
            raise RequestSuperseded()
        with torch.no_grad():
            for inputs, pause_sec in tokenized_segments:
                if inputs is None:
                    audio_parts.append(np.zeros(int(sr * pause_sec), dtype=np.float32))
                    continue
                # Check superseding between segments (cooperative abort).
                if my_seq is not None and not _is_current(my_seq):
                    raise RequestSuperseded()
                output = model(**inputs).waveform
                audio = output[0].float().cpu().numpy().astype(np.float32)
                audio_parts.append(audio)
                if pause_sec > 0:
                    audio_parts.append(np.zeros(int(sr * pause_sec), dtype=np.float32))

    if not audio_parts:
        raise RuntimeError("MMS produced no audio segments")

    return np.concatenate(audio_parts), sr


# ---------------------------------------------------------------------------
# Engine: AI4Bharat FastPitch + HiFiGAN (13 Indian languages)
# ---------------------------------------------------------------------------
# Fully parallel (non-autoregressive) — generates mel spectrograms in one
# forward pass, then HiFiGAN converts to audio. RTF ~0.5-0.8 even on CPU.
# Male + female speakers per language. Handles punctuation natively.

def _get_fastpitch(lang_code: str, speaker: str = "female"):
    """Lazy-load a FastPitch + HiFiGAN synthesizer for the given language.

    Returns a Coqui TTS Synthesizer instance. Cached per (lang, speaker) pair.
    """
    cache: dict = app.state.fastpitch_cache
    cache_key = f"{lang_code}_{speaker}"
    if cache_key in cache:
        return cache[cache_key]

    with app.state.fastpitch_lock:
        if cache_key in cache:
            return cache[cache_key]

        from TTS.utils.synthesizer import Synthesizer

        model_dir = os.path.join(FASTPITCH_MODELS_DIR, lang_code)
        fp_model = os.path.join(model_dir, "fastpitch", "best_model.pth")
        fp_config = os.path.join(model_dir, "fastpitch", "config.json")
        hfg_model = os.path.join(model_dir, "hifigan", "best_model.pth")
        hfg_config = os.path.join(model_dir, "hifigan", "config.json")

        if not os.path.exists(fp_model):
            raise HTTPException(
                status_code=500,
                detail=f"FastPitch model not found for language '{lang_code}' at {fp_model}",
            )

        logger.info("Loading FastPitch + HiFiGAN for %s (speaker=%s)", lang_code, speaker)
        synth = Synthesizer(
            tts_checkpoint=fp_model,
            tts_config_path=fp_config,
            vocoder_checkpoint=hfg_model,
            vocoder_config=hfg_config,
            use_cuda=False,  # CPU is fast enough (RTF<1) and avoids GPU contention with Qwen
        )
        cache[cache_key] = synth
        logger.info("FastPitch %s loaded (sample_rate=%d)", lang_code, synth.output_sample_rate)
        return synth


def _resolve_fastpitch_speaker(voice_id: str) -> str:
    """Extract speaker gender from voice_id like 'indic-hindi-male' -> 'male'."""
    if voice_id and voice_id.endswith("-male"):
        return "male"
    return "female"


def _fastpitch_synthesize(text: str, lang_code: str, speaker: str = "female", my_seq: int | None = None) -> tuple[np.ndarray, int]:
    """Synthesize text using AI4Bharat FastPitch + HiFiGAN.

    Runs on CPU (fully parallel, RTF < 1.0) so it doesn't contend with
    Qwen3 for the GPU.
    """
    if my_seq is not None and not _is_current(my_seq):
        raise RequestSuperseded()

    synth = _get_fastpitch(lang_code, speaker)
    sr = synth.output_sample_rate

    # Pre-process text for FastPitch's limited vocabulary
    clean = _preprocess_for_fastpitch(text, lang_code)

    if not clean:
        raise RuntimeError("FastPitch: text is empty after preprocessing")

    # Synthesize (Coqui TTS handles sentence splitting internally via pysbd)
    wav = synth.tts(clean, speaker_name=speaker)

    if my_seq is not None and not _is_current(my_seq):
        raise RequestSuperseded()

    audio = np.array(wav, dtype=np.float32)
    if len(audio) == 0:
        raise RuntimeError(f"FastPitch produced empty audio for lang={lang_code}")

    return audio, sr


# Regex to find runs of Latin characters (English words in Hindi text)
_LATIN_WORD_RE = re.compile(r"[A-Za-z]+")
# Regex to find remaining digit sequences (should be rare after backend normalization)
_DIGIT_RE = re.compile(r"\d+")

# Hindi digit words for any digits that slip through
_HINDI_DIGITS = ["शून्य", "एक", "दो", "तीन", "चार", "पाँच", "छः", "सात", "आठ", "नौ"]


def _digits_to_hindi_words(match: re.Match) -> str:
    """Convert a digit sequence to Hindi digit words (digit by digit for short,
    or as a number word for longer sequences)."""
    digits = match.group(0)
    # Read digit by digit (safest for any remaining numbers)
    return " ".join(_HINDI_DIGITS[int(d)] for d in digits)


def _preprocess_for_fastpitch(text: str, lang_code: str) -> str:
    """Comprehensive text preprocessing for FastPitch Indian language models.

    Handles:
    - Emojis → stripped
    - Hindi danda/double danda → period (for sentence pauses)
    - Em-dash, en-dash → comma (for clause pauses)
    - English words → stripped (backend normalizer should have converted them)
    - Remaining digits → Hindi number words
    - Markdown/symbols → stripped
    - Unsupported punctuation → mapped to supported equivalents
    """
    clean = text

    # 0. Strip emojis FIRST (they're multi-byte and break everything)
    clean = re.sub(
        "["
        "\U0001F300-\U0001F9FF"
        "\U0001FA00-\U0001FAFF"
        "\U00002600-\U000027BF"
        "\U00002B00-\U00002BFF"
        "\U0000FE00-\U0000FE0F"
        "\U0000200D"
        "\U000000A9\U000000AE"
        "\U00002122\U00002139"
        "\U0000203C\U00002049"
        "\U0001F000-\U0001F0FF"
        "\U0001F100-\U0001F1FF"
        "\U000020E3"
        "]+", "", clean
    )

    # 1. Map unsupported punctuation to supported equivalents
    clean = clean.replace("\u0964", ".")   # । (danda) -> period
    clean = clean.replace("\u0965", ".")   # ॥ (double danda) -> period
    clean = clean.replace("\u2014", ",")   # — (em-dash) -> comma
    clean = clean.replace("\u2013", ",")   # – (en-dash) -> comma
    clean = clean.replace("\u2026", ".")   # … -> period
    clean = clean.replace('"', "'")        # smart quotes -> apostrophe
    clean = clean.replace('\u201c', "'")
    clean = clean.replace('\u201d', "'")
    clean = clean.replace('\u2018', "'")
    clean = clean.replace('\u2019', "'")
    clean = clean.replace('`', "'")

    # 2. Strip markdown and symbols not in vocab
    clean = re.sub(r"[#*_~\[\]{}|\\@&%$₹€£¥+=<>^/]", "", clean)

    # 3. Remove English words entirely (FastPitch Hindi has no Latin chars)
    if lang_code in ("hi", "ta", "te", "mr", "bn", "gu", "kn", "ml", "pa"):
        clean = _LATIN_WORD_RE.sub("", clean)

    # 4. Convert any remaining digits to spoken words
    clean = _DIGIT_RE.sub(_digits_to_hindi_words, clean)

    # 5. Collapse whitespace and clean up punctuation artifacts
    clean = re.sub(r"\s+", " ", clean).strip()
    # Remove orphan punctuation (e.g., ", ," or ". ." from stripped words)
    clean = re.sub(r"[,.\s]+([,.])", r"\1", clean)
    clean = re.sub(r"([,.])\s*([,.])", r"\1", clean)
    # Remove leading/trailing punctuation-only fragments
    clean = re.sub(r"^\s*[,.;:]+\s*", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()

    return clean


# ---------------------------------------------------------------------------
# Routing + encoding
# ---------------------------------------------------------------------------
def _check_auth(xi_api_key: Optional[str]) -> None:
    if not API_KEY:
        return
    if xi_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")


# Backward-compat: map old MMS voice IDs to new FastPitch voice IDs.
_VOICE_COMPAT_MAP: dict[str, str] = {
    "mms-hindi": "indic-hindi-female",
    "mms-tamil": "indic-tamil-female",
    "mms-telugu": "indic-telugu-female",
    "mms-marathi": "indic-marathi-female",
    "mms-bengali": "indic-bengali-female",
    "mms-gujarati": "indic-gujarati-female",
    "mms-kannada": "indic-kannada-female",
    "mms-malayalam": "indic-malayalam-female",
    "mms-punjabi": "indic-punjabi-female",
}

# Map indic voice IDs to their FastPitch language code for voice-based routing.
_INDIC_VOICE_TO_LANG: dict[str, str] = {}
for _v in VOICE_CATALOG:
    if _v["voice_id"].startswith("indic-"):
        # "indic-hindi-female" -> "hi" (first language in the voice's list)
        _INDIC_VOICE_TO_LANG[_v["voice_id"]] = _v["languages"][0].lower().split("-")[0]


def _resolve_voice(voice_id: str) -> str:
    vid = (voice_id or "").strip()
    if not vid:
        return DEFAULT_VOICE_ID
    # Backward compat: translate old mms-* IDs to new indic-* IDs
    vid = _VOICE_COMPAT_MAP.get(vid, vid)
    for v in VOICE_CATALOG:
        if v["voice_id"] == vid:
            return v["voice_id"]
    return DEFAULT_VOICE_ID


def _override_engine_by_voice(engine: str, arg: str, preprocess, voice: str):
    """If the resolved voice is an indic-* voice, force FastPitch engine
    regardless of what language_code said. This handles cases where the
    frontend sends voice_id=indic-hindi-female with language_code=en."""
    if voice in _INDIC_VOICE_TO_LANG:
        lang = _INDIC_VOICE_TO_LANG[voice]
        fp_lang = FASTPITCH_LANG_MAP.get(lang, lang)
        return "fastpitch", fp_lang, preprocess
    return engine, arg, preprocess


def _route_engine(language_code: Optional[str]) -> tuple[str, str, str | None]:
    """Return (engine_name, engine_arg, preprocess) where:

    - engine_name is "qwen", "fastpitch", or "mms"
    - engine_arg is the Qwen language label, FastPitch lang code, or MMS ISO 639-3 suffix
    - preprocess is None or a tag like "latn-to-devanagari" telling the
      caller to transform text before sending it to the engine
    """
    if not language_code:
        return "qwen", DEFAULT_LANGUAGE, None

    raw = language_code.strip().lower()
    base = raw.split("-")[0]

    # Hi-Latn = Hinglish: romanized Hindi -> transliterate to Devanagari for FastPitch
    if raw == "hi-latn":
        return "fastpitch", FASTPITCH_LANG_MAP["hi-latn"], "latn-to-devanagari"

    # Qwen handles English + CJK + European languages
    if base in QWEN_LANG_MAP:
        return "qwen", QWEN_LANG_MAP[base], None

    # FastPitch handles 13 Indian languages (preferred over MMS)
    if raw in FASTPITCH_LANG_MAP:
        return "fastpitch", FASTPITCH_LANG_MAP[raw], None
    if base in FASTPITCH_LANG_MAP:
        return "fastpitch", FASTPITCH_LANG_MAP[base], None

    # MMS fallback for remaining languages (Urdu, Arabic)
    if raw in MMS_LANG_MAP:
        return "mms", MMS_LANG_MAP[raw], None
    if base in MMS_LANG_MAP:
        return "mms", MMS_LANG_MAP[base], None

    return "qwen", "auto", None


def _encode_audio(audio: np.ndarray, sr: int, output_format: Optional[str]) -> tuple[bytes, str]:
    """Return (bytes, mime) for the requested output format. Default mp3."""
    fmt = (output_format or "mp3_44100_128").strip().lower()

    if fmt.startswith("pcm"):
        try:
            target_sr = int(fmt.split("_", 1)[1]) if "_" in fmt else sr
        except ValueError:
            target_sr = sr
        if target_sr != sr:
            n_in = audio.shape[0]
            n_out = int(round(n_in * target_sr / sr))
            audio = np.interp(
                np.linspace(0, n_in - 1, n_out, dtype=np.float64),
                np.arange(n_in, dtype=np.float64),
                audio,
            ).astype(np.float32)
            sr = target_sr
        pcm16 = (np.clip(audio, -1.0, 1.0) * 32767.0).astype(np.int16)
        return pcm16.tobytes(), f"audio/L16;rate={sr}"

    buffer = io.BytesIO()
    if fmt.startswith("wav") or fmt.startswith("pcm_wav"):
        sf.write(buffer, audio, sr, format="WAV")
        return buffer.getvalue(), "audio/wav"

    try:
        sf.write(buffer, audio, sr, format="MP3")
        return buffer.getvalue(), "audio/mpeg"
    except Exception:
        buffer = io.BytesIO()
        sf.write(buffer, audio, sr, format="WAV")
        return buffer.getvalue(), "audio/wav"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> dict:
    qwen_loaded = hasattr(app.state, "qwen_model") and app.state.qwen_model is not None
    mms_loaded = list((app.state.mms_cache or {}).keys()) if hasattr(app.state, "mms_cache") else []
    return {
        "status": "ok" if qwen_loaded else "loading",
        "device": DEVICE,
        "dtype": DTYPE_STR,
        "engines": {
            "qwen": {"loaded": qwen_loaded, "model_id": QWEN_MODEL_ID, "languages": sorted(QWEN_SUPPORTED_LANGS)},
            "mms": {"loaded_languages": mms_loaded, "available_codes": sorted(set(MMS_LANG_MAP.values()))},
        },
    }


@app.get("/v1/voices")
def list_voices(
    xi_api_key: Optional[str] = Header(default=None, alias="xi-api-key"),
):
    _check_auth(xi_api_key)
    
    # Return all voices - client will filter by language if needed
    return {"voices": VOICE_CATALOG}


@app.post("/v1/text-to-speech/{voice_id}")
def text_to_speech(
    body: TTSRequestBody,
    voice_id: str = Path(...),
    xi_api_key: Optional[str] = Header(default=None, alias="xi-api-key"),
    accept: Optional[str] = Header(default=None),
):
    _check_auth(xi_api_key)
    if not hasattr(app.state, "qwen_model") or app.state.qwen_model is None:
        raise HTTPException(status_code=503, detail="model not loaded")

    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is empty")

    engine, arg, preprocess = _route_engine(body.language_code)
    voice = _resolve_voice(voice_id)
    # Override engine if voice is an indic-* voice (handles mismatched language_code)
    engine, arg, preprocess = _override_engine_by_voice(engine, arg, preprocess, voice)
    
    # Check cache first (skip for very short text to avoid cache overhead)
    cache_key = None
    if len(text) > 20:  # Only cache longer texts
        cache_key = _make_cache_key(text, engine, arg, voice)
        cached_audio, cached_sr = _get_cached_tts(cache_key)
        if cached_audio is not None:
            logger.info("Cache hit engine=%s arg=%s voice=%s len=%d", engine, arg, voice, len(text))
            output_format = body.output_format
            if not output_format and accept:
                a = accept.lower()
                if "audio/wav" in a:
                    output_format = "wav"
                elif "audio/mpeg" in a:
                    output_format = "mp3_44100_128"
            
            payload, mime = _encode_audio(cached_audio, cached_sr, output_format)
            return Response(
                content=payload,
                media_type=mime,
                headers={
                    "X-Voice-Id": voice_id,
                    "X-Engine": engine,
                    "X-Language": arg,
                    "X-Sample-Rate": str(cached_sr),
                    "X-Cache-Hit": "true",
                },
            )
    
    # Claim a generation: this supersedes any older in-flight synthesis
    my_seq = _claim_request()
    logger.info("synth seq=%d engine=%s arg=%s voice=%s preprocess=%s len=%d", my_seq, engine, arg, voice, preprocess, len(text))

    if preprocess == "latn-to-devanagari":
        text = _latn_to_devanagari(text)

    try:
        if engine == "qwen":
            audio, sr = _qwen_synthesize(text, arg, speaker=voice, my_seq=my_seq)
        elif engine == "fastpitch":
            fp_speaker = _resolve_fastpitch_speaker(voice)
            audio, sr = _fastpitch_synthesize(text, arg, speaker=fp_speaker, my_seq=my_seq)
        else:
            audio, sr = _mms_synthesize(text, arg, my_seq=my_seq)
    except RequestSuperseded:
        logger.info("synth seq=%d superseded by newer request", my_seq)
        _finish_request(my_seq)
        raise HTTPException(status_code=409, detail="superseded by a newer TTS request")
    except Exception as exc:
        logger.exception("tts generation failed (engine=%s arg=%s)", engine, arg)
        _finish_request(my_seq)
        raise HTTPException(status_code=500, detail=f"tts generation failed: {exc}") from exc
    # Cache TTS response for future requests (only for longer texts)
    if cache_key and len(text) > 20:
        _cache_tts(cache_key, audio, sr)
    
    # Clean up request tracking
    _finish_request(my_seq)

    output_format = body.output_format
    if not output_format and accept:
        a = accept.lower()
        if "audio/wav" in a:
            output_format = "wav"
        elif "audio/mpeg" in a:
            output_format = "mp3_44100_128"

    payload, mime = _encode_audio(audio, sr, output_format)
    return Response(
        content=payload,
        media_type=mime,
        headers={
            "X-Voice-Id": voice_id,
            "X-Engine": engine,
            "X-Language": arg,
            "X-Sample-Rate": str(sr),
        },
    )


@app.post("/v1/text-to-speech-stream/{voice_id}")
def text_to_speech_stream(
    body: TTSRequestBody,
    voice_id: str = Path(...),
    xi_api_key: Optional[str] = Header(default=None, alias="xi-api-key"),
):
    """Realtime TTS: stream raw PCM16 (mono) frames as the model renders them.

    For Qwen voices this forwards each ~0.67s sub-chunk the instant
    FasterQwen3TTS produces it (first chunk in ~680ms on a T4), so the caller
    can start playback immediately instead of waiting for the whole clip.
    MMS voices have no incremental API, so we render once and emit a single
    frame. The response is a chunked stream of little-endian int16 samples;
    the sample rate is sent in the X-Sample-Rate header before the body.
    """
    _check_auth(xi_api_key)
    if not hasattr(app.state, "qwen_model") or app.state.qwen_model is None:
        raise HTTPException(status_code=503, detail="model not loaded")

    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is empty")

    engine, arg, preprocess = _route_engine(body.language_code)
    voice = _resolve_voice(voice_id)
    # Override engine if voice is an indic-* voice (handles mismatched language_code)
    engine, arg, preprocess = _override_engine_by_voice(engine, arg, preprocess, voice)
    # Claim a generation so this stream supersedes any older in-flight request.
    my_seq = _claim_request()
    logger.info("stream seq=%d engine=%s arg=%s voice=%s preprocess=%s len=%d", my_seq, engine, arg, voice, preprocess, len(text))

    if preprocess == "latn-to-devanagari":
        text = _latn_to_devanagari(text)

    # Sample rate is fixed per engine (Qwen 24k, FastPitch 22.05k, MMS 16k).
    if engine == "qwen":
        sample_rate = 24000
    elif engine == "fastpitch":
        sample_rate = 22050
    else:
        sample_rate = 16000

    def _pcm_frames():
        try:
            if engine == "qwen":
                for arr, _sr in _qwen_stream(text, arg, speaker=voice, my_seq=my_seq):
                    pcm16 = (np.clip(arr, -1.0, 1.0) * 32767.0).astype("<i2")
                    yield pcm16.tobytes()
            elif engine == "fastpitch":
                fp_speaker = _resolve_fastpitch_speaker(voice)
                audio, _sr = _fastpitch_synthesize(text, arg, speaker=fp_speaker, my_seq=my_seq)
                pcm16 = (np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2")
                yield pcm16.tobytes()
            else:
                audio, _sr = _mms_synthesize(text, arg, my_seq=my_seq)
                pcm16 = (np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2")
                yield pcm16.tobytes()
        except RequestSuperseded:
            logger.info("stream seq=%d superseded by newer request", my_seq)
            return
        except Exception as exc:  # pragma: no cover
            logger.exception("stream tts failed (engine=%s arg=%s)", engine, arg)
            # Can't change status mid-stream; just stop. Caller sees a short body.
            return
        finally:
            # Clean up request tracking
            _finish_request(my_seq)

    return StreamingResponse(
        _pcm_frames(),
        media_type="audio/L16",
        headers={
            "X-Voice-Id": voice_id,
            "X-Engine": engine,
            "X-Language": arg,
            "X-Sample-Rate": str(sample_rate),
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@app.exception_handler(HTTPException)
async def http_exc_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": {"status": "error", "message": str(exc.detail)}},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        workers=1,
        reload=False,
    )
