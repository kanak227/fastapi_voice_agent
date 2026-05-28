FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    UVICORN_RELOAD=0 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Layer 1 — gateway dependencies (FastAPI, Redis, etc.)
# ---------------------------------------------------------------------------
COPY fastapi_server/requirements.txt /tmp/requirements-gateway.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements-gateway.txt

# ---------------------------------------------------------------------------
# Layer 2 — shared bot dependencies (LangChain, Qdrant, Google Generative AI)
# Most of these overlap with the gateway requirements; pip de-dupes them.
# ---------------------------------------------------------------------------
COPY tekurious-chatbot-main/bots/requirements-shared.txt /tmp/requirements-bots.txt
RUN pip install --no-cache-dir -r /tmp/requirements-bots.txt

# ---------------------------------------------------------------------------
# Layer 3 — application code
# ---------------------------------------------------------------------------
# Gateway code becomes the top-level `app` package.
COPY fastapi_server/app /app/app

# Each bot's source tree lives next to the proxy entrypoint at /app/<bot>/src.
COPY tekurious-chatbot-main/bots/religious-ai/src               /app/religious-ai/src
COPY tekurious-chatbot-main/bots/education-ai/src               /app/education-ai/src
COPY tekurious-chatbot-main/bots/digital-literacy-ai/src        /app/digital-literacy-ai/src
COPY tekurious-chatbot-main/bots/design-thinking-ai/src         /app/design-thinking-ai/src
COPY tekurious-chatbot-main/bots/wellbeing-ai/src               /app/wellbeing-ai/src
COPY tekurious-chatbot-main/bots/sustainability-ai/src          /app/sustainability-ai/src
COPY tekurious-chatbot-main/bots/global-citizenship-ai/src      /app/global-citizenship-ai/src
COPY tekurious-chatbot-main/bots/entrepreneurship-ai/src        /app/entrepreneurship-ai/src
COPY tekurious-chatbot-main/bots/emotional-intelligence-ai/src  /app/emotional-intelligence-ai/src
COPY tekurious-chatbot-main/bots/financial-literacy-ai/src      /app/financial-literacy-ai/src

# The merged entrypoint that boots gateway + bot subprocesses.
COPY tekurious-chatbot-main/bots/multi_bot_server/merged_main.py /app/merged_main.py

# Cloud Run scratch storage (used for SQLite in dev; ephemeral here).
RUN mkdir -p storage

EXPOSE 8080

# Single uvicorn worker — each bot subprocess has its own worker, the
# merged process is mostly I/O bound (proxying + Gemini calls).
CMD ["python", "-m", "uvicorn", "merged_main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
