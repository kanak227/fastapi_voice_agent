# Qwen3 TTS service — runs on a T4 GPU VM (ElevenLabs-compatible API).
# Base image ships CUDA 12.4 + cuDNN runtime; matches torch >= 2.5 wheels.
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.11 python3.11-venv python3-pip \
        libsndfile1 ffmpeg ca-certificates curl unzip \
        sox libsox-fmt-all \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/python3.11 /usr/bin/python3

WORKDIR /app

COPY requirements.txt .
# Install TTS (Coqui) first — it pins transformers<=4.46 but works fine with 4.57.
# Then install the rest which pulls in transformers==4.57.3 via qwen-tts, overriding.
RUN python -m pip install --upgrade pip && \
    pip install --extra-index-url https://download.pytorch.org/whl/cu124 \
        'numpy>=1.26.0,<2.0' 'TTS>=0.22.0' && \
    pip install --extra-index-url https://download.pytorch.org/whl/cu124 -r requirements.txt

COPY server.py .

# FastPitch model checkpoints live on the persistent volume (/models/fastpitch)
# mounted at runtime, NOT baked into the image. This keeps the image lean.
ENV FASTPITCH_MODELS_DIR=/models/fastpitch

ENV PORT=8000 \
    QWEN_DEVICE=cuda \
    QWEN_DTYPE=float32

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=300s --retries=3 \
    CMD curl -fsS http://localhost:${PORT}/health || exit 1

CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
