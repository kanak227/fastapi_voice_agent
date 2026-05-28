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
import threading
from typing import Optional

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, Header, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from qwen_tts import Qwen3TTSModel


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
QWEN_MODEL_ID = os.getenv("QWEN_MODEL_ID", "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice")
DEVICE = os.getenv("QWEN_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
DTYPE_STR = os.getenv("QWEN_DTYPE", "float16" if torch.cuda.is_available() else "float32").lower()
DEFAULT_VOICE_ID = os.getenv("QWEN_DEFAULT_VOICE_ID", "serena")
DEFAULT_LANGUAGE = os.getenv("QWEN_DEFAULT_LANGUAGE", "english")
SEED = int(os.getenv("QWEN_SEED", "1234"))
API_KEY = os.getenv("TTS_API_KEY", "")  # optional, blank = no auth

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
MMS_LANG_MAP: dict[str, str] = {
    "hi": "hin",
    "hi-latn": "hin",  # romanized Hindi reads back as Hindi audio
    "ta": "tam",
    "te": "tel",
    "mr": "mar",
    "bn": "ben",
    "gu": "guj",
    "kn": "kan",
    "ml": "mal",
    "pa": "pan",
    "ur": "urd",
    "ar": "ara",
}


# Voice catalog. The voice_id is what the chatbot sends in the URL path.
# When the underlying engine is MMS-TTS the voice is irrelevant (single
# speaker per language) but we still expose names for UI consistency.
VOICE_CATALOG: list[dict] = [
    {"voice_id": "serena", "name": "Serena", "labels": {"gender": "female", "accent": "neutral"}, "languages": ["en", "fr", "de", "es", "it", "pt", "ru", "ja", "ko", "zh"]},
    {"voice_id": "ethan", "name": "Ethan", "labels": {"gender": "male", "accent": "neutral"}, "languages": ["en", "fr", "de", "es", "it", "pt", "ru", "ja", "ko", "zh"]},
    {"voice_id": "mms-hindi", "name": "Hindi (MMS)", "labels": {"gender": "neutral", "accent": "hindi"}, "languages": ["hi"]},
    {"voice_id": "mms-tamil", "name": "Tamil (MMS)", "labels": {"gender": "neutral", "accent": "tamil"}, "languages": ["ta"]},
    {"voice_id": "mms-telugu", "name": "Telugu (MMS)", "labels": {"gender": "neutral", "accent": "telugu"}, "languages": ["te"]},
    {"voice_id": "mms-marathi", "name": "Marathi (MMS)", "labels": {"gender": "neutral", "accent": "marathi"}, "languages": ["mr"]},
    {"voice_id": "mms-bengali", "name": "Bengali (MMS)", "labels": {"gender": "neutral", "accent": "bengali"}, "languages": ["bn"]},
    {"voice_id": "mms-gujarati", "name": "Gujarati (MMS)", "labels": {"gender": "neutral", "accent": "gujarati"}, "languages": ["gu"]},
    {"voice_id": "mms-kannada", "name": "Kannada (MMS)", "labels": {"gender": "neutral", "accent": "kannada"}, "languages": ["kn"]},
    {"voice_id": "mms-malayalam", "name": "Malayalam (MMS)", "labels": {"gender": "neutral", "accent": "malayalam"}, "languages": ["ml"]},
    {"voice_id": "mms-punjabi", "name": "Punjabi (MMS)", "labels": {"gender": "neutral", "accent": "punjabi"}, "languages": ["pa"]},
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
    logger.info("Loading Qwen3-TTS %s on %s (dtype=%s)", QWEN_MODEL_ID, DEVICE, DTYPE_STR)
    _set_seed(SEED)
    app.state.qwen_model = Qwen3TTSModel.from_pretrained(
        QWEN_MODEL_ID,
        device_map=DEVICE,
        torch_dtype=TORCH_DTYPE,
    )
    app.state.qwen_lock = threading.Lock()
    # MMS models are lazy-loaded on first use to keep startup fast and
    # memory low when only some languages are actually used.
    app.state.mms_cache: dict[str, tuple] = {}
    app.state.mms_lock = threading.Lock()
    app.state.uroman = None  # lazy-init
    logger.info("Qwen3-TTS ready. MMS engines will load on demand.")


def _qwen_synthesize(text: str, language: str, speaker: str = None) -> tuple[np.ndarray, int]:
    speaker = speaker or DEFAULT_VOICE_ID
    with app.state.qwen_lock:
        _set_seed(SEED)
        wavs, sr = app.state.qwen_model.generate_custom_voice(
            text=text,
            speaker=speaker,
            language=language,
        )
    if not wavs:
        raise RuntimeError("Qwen3 returned empty audio")
    audio = wavs[0]
    if hasattr(audio, "cpu"):
        audio = audio.cpu().numpy()
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


def _mms_synthesize(text: str, lang_iso639_3: str) -> tuple[np.ndarray, int]:
    model, tokenizer, is_uroman, lock = _get_mms(lang_iso639_3)
    input_text = _romanize(text) if is_uroman else text
    inputs = tokenizer(input_text, return_tensors="pt").to(DEVICE)
    with lock:
        with torch.no_grad():
            output = model(**inputs).waveform
    audio = output[0].float().cpu().numpy()
    return audio.astype(np.float32), int(model.config.sampling_rate)


# ---------------------------------------------------------------------------
# Routing + encoding
# ---------------------------------------------------------------------------
def _check_auth(xi_api_key: Optional[str]) -> None:
    if not API_KEY:
        return
    if xi_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")


def _resolve_voice(voice_id: str) -> str:
    vid = (voice_id or "").strip()
    if not vid:
        return DEFAULT_VOICE_ID
    for v in VOICE_CATALOG:
        if v["voice_id"] == vid:
            return v["voice_id"]
    return DEFAULT_VOICE_ID


def _route_engine(language_code: Optional[str]) -> tuple[str, str, str | None]:
    """Return (engine_name, engine_arg, preprocess) where:

    - engine_name is "qwen" or "mms"
    - engine_arg is the Qwen language label or the MMS ISO 639-3 suffix
    - preprocess is None or a tag like "latn-to-devanagari" telling the
      caller to transform text before sending it to the engine
    """
    if not language_code:
        return "qwen", DEFAULT_LANGUAGE, None

    raw = language_code.strip().lower()
    base = raw.split("-")[0]

    # Hi-Latn = Hinglish: the user typed/said romanized Hindi. Convert to
    # Devanagari so MMS Hindi can synthesize it.
    if raw == "hi-latn":
        return "mms", MMS_LANG_MAP["hi-latn"], "latn-to-devanagari"

    if base in QWEN_LANG_MAP:
        return "qwen", QWEN_LANG_MAP[base], None

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
    logger.info("synth engine=%s arg=%s voice=%s preprocess=%s len=%d", engine, arg, voice, preprocess, len(text))

    if preprocess == "latn-to-devanagari":
        text = _latn_to_devanagari(text)

    try:
        if engine == "qwen":
            audio, sr = _qwen_synthesize(text, arg, speaker=voice)
        else:
            audio, sr = _mms_synthesize(text, arg)
    except Exception as exc:
        logger.exception("tts generation failed (engine=%s arg=%s)", engine, arg)
        raise HTTPException(status_code=500, detail=f"tts generation failed: {exc}") from exc

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
