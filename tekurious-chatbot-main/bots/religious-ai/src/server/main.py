import os
import re
import logging
import traceback
import uuid
from typing import Any
import json
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, File, UploadFile, Form, Header
from langchain.output_parsers import PydanticOutputParser
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

# from llm.gemini import get_gemini_engine

from llm.dynamic_llm import run_bot, run_bot_stream

from fastapi.responses import JSONResponse, StreamingResponse
from pathlib import Path
from llm.output_parser import ParseOutput
from llm.input import ParseInput
from utils.common import DHOME
from guardrails.guardrails import Guardrails

from server.playground import register_playground

try:
    from google.api_core.exceptions import ResourceExhausted as _GeminiResourceExhausted
except Exception:  # pragma: no cover
    _GeminiResourceExhausted = None


def _load_env():
    base_dir = Path(__file__).resolve().parents[1]
    load_dotenv(base_dir / ".env", override=False)


_load_env()

log = logging.getLogger("religious-ai.chat")

# For speech-to-speech POC


malicious_pattern = re.compile(r"\$\(\s*(\w+)\s*.*?\)")

def is_malicious(data: Any) -> bool:
    """
    Recursively checks if the given data contains malicious patterns.

    Args:
        data (Any): The data to check, which can be a dictionary, list, or string.

    Returns:
        bool: True if malicious patterns are detected, False otherwise.
    """
    if isinstance(data, dict):
        return any(is_malicious(value) for value in data.values())
    elif isinstance(data, list):
        return any(is_malicious(item) for item in data)
    elif isinstance(data, str):
        return bool(malicious_pattern.search(data))
    return False

def validate_data(data_dict, request_type):
    
    if request_type == "chat" and "query" in data_dict and data_dict["query"] in ["", None, "null"]:
        return False, "Either query is not present or its valuse is invalid."
    
    return True, "valid"


def _wants_event_stream(accept: str | None) -> bool:
    if not accept:
        return False
    lower = accept.lower()
    return "text/event-stream" in lower or "*/*" in lower


def _sse(event: str, data_obj: Any) -> bytes:
    if isinstance(data_obj, (dict, list)):
        payload = json.dumps(data_obj, ensure_ascii=True)
    else:
        payload = json.dumps(str(data_obj), ensure_ascii=True)
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


def get_llm_response(query: str) -> ParseOutput:
    llm_engine = get_llm_engine()
    prompt_path = Path(__file__).resolve().parents[1] / "prompts" / "analyze_query.yaml"
    llm_engine.prompt = llm_engine.load_prompt(prompt_path)
    
    if not llm_engine.prompt:
        raise ValueError(f"Prompt couldn't be assigned to {llm_engine.provider} engine. Please load the prompt and initialize the chain.")

    llm_engine.set_output_parser(PydanticOutputParser(pydantic_object=ParseOutput))
    llm_engine.get_llm_sequence(llm_engine.prompt)
    query_model = ParseInput(query=query)
    
    result = llm_engine.respond(query_model)
    
    return result
""" 
def get_llm_response(query: str ) -> ParseOutput:
    gemini_engine = get_gemini_engine()
    prompt_path = os.path.join("prompts", "analyze_query.yaml")
    print("prompt_path:", prompt_path)
    gemini_engine.prompt = gemini_engine.load_prompt(Path(prompt_path))

    if not gemini_engine.prompt:
        raise ValueError("Prompt couldn't be assigned to GeminiEngine. Please load the prompt and initialize the chain.")

    gemini_engine.set_output_parser(PydanticOutputParser(pydantic_object=ParseOutput))
    gemini_engine.get_llm_sequence(gemini_engine.prompt)
    query_model = ParseInput(query=query)
    
    result = gemini_engine.respond(query_model)

    return result
"""

app = FastAPI()

register_playground(app, "Darshan AI - Religious (standalone)")

logger = logging.getLogger("uvicorn.error")


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "darshan-ai",
        "endpoints": {"chat": "/chat", "playground": "/playground", "docs": "/docs", "health": "/health"},
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(status_code=204, content=None)

@app.post("/chat")
async def chat(request: Request, accept: str | None = Header(default=None)):
    request_id = (request.headers.get("x-request-id") or "").strip() or str(uuid.uuid4())
    tenant_id = (request.headers.get("x-tenant-id") or "").strip()
    try:
        expected = (os.getenv("SERVICE_TOKEN") or "").strip()
        if expected:
            offered = (request.headers.get("x-service-token") or "").strip()
            if offered != expected:
                raise HTTPException(status_code=403, detail="Invalid or missing service token")

        data_dict = dict(request.query_params)
        if not data_dict:
            try:
                body = await request.json()
                if isinstance(body, dict) and "query" in body:
                    data_dict = {
                        "query": body.get("query"),
                        "history": body.get("history", []),
                        "input_type": body.get("input_type", "text"),
                        "language": body.get("language", "en-US"),
                    }
            except Exception:
                pass

        if is_malicious(data_dict):
            log.warning(
                "malicious_payload request_id=%s tenant_id=%s data=%s",
                request_id,
                tenant_id,
                data_dict,
            )
            raise HTTPException(status_code=400, detail="Malicious payload detected")

        val_status, msg = validate_data(data_dict, "chat")
        if not val_status:
            log.info("validation_failed request_id=%s tenant_id=%s msg=%s", request_id, tenant_id, msg)
            raise HTTPException(status_code=404, detail="ERR-101:" + msg)

        query = data_dict["query"]
        history = data_dict.get("history", [])

        guardrails = Guardrails()
        input_type = data_dict.get("input_type", "text")
        is_voice = input_type in ("voice", "audio")

        # For voice input, the frontend already validated the transcript against
        # domain guardrails (isReligiousTopicAllowedByIntent). Skip the LLM-based
        # guardrail here to avoid false rejections from non-deterministic LLM responses
        # on short STT transcripts. The RAG pipeline still has its own scope check.
        if is_voice:
            guardrails_output = "YES"
            exp = "Voice input — frontend guardrail already passed"
        else:
            try:
                guardrails_output, exp = guardrails.apply_input_guardrails(query, history)
            except Exception as e:
                log.warning("guardrails_failed request_id=%s error=%s", request_id, str(e))
                guardrails_output = "YES"
                exp = "Guardrails failed, allowing query"
        
        if not guardrails_output or guardrails_output.strip().upper() != "YES":
            refusal = "Sorry, I can only help with Indian religious mythology topics."
            if _wants_event_stream(accept):

                async def refuse_stream():
                    yield _sse("text", refusal)
                    yield _sse("done", {"ok": True, "request_id": request_id})

                return StreamingResponse(refuse_stream(), media_type="text/event-stream")
            return {"response": refusal, "request_id": request_id}

        domain_label = "Indian religion and spirituality"
        response_language = data_dict.get("language", "en-US") or "en-US"

        if _wants_event_stream(accept):

            async def event_stream():
                try:
                    async for piece in run_bot_stream(
                        query=query,
                        domain=domain_label,
                        request_id=request_id,
                        tenant_id=tenant_id,
                        history=history,
                        is_voice=is_voice,
                        response_language=response_language,
                    ):
                        yield _sse("text", piece)
                    yield _sse("done", {"ok": True, "request_id": request_id})
                except Exception:
                    log.exception("chat_stream_failed request_id=%s", request_id)
                    yield _sse(
                        "done",
                        {"ok": False, "request_id": request_id, "detail": "stream_failed"},
                    )

            return StreamingResponse(event_stream(), media_type="text/event-stream")

        response = run_bot(
            query=query,
            domain=domain_label,
            request_id=request_id,
            tenant_id=tenant_id,
            history=history,
            is_voice=is_voice,
            response_language=response_language,
        )
        log.info("chat_ok request_id=%s tenant_id=%s", request_id, tenant_id)
        return {"response": response, "request_id": request_id}
    except HTTPException as err:
        raise err
    except (ValueError, ImportError) as e:
        err_text = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        log.error("chat_failed request_id=%s tenant_id=%s error=%s", request_id, tenant_id, err_text)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Upstream LLM error. Please try again.",
                "request_id": request_id,
            },
        )
    except Exception as e:
        if _GeminiResourceExhausted is not None and isinstance(e, _GeminiResourceExhausted):
            log.warning("gemini_quota request_id=%s tenant_id=%s", request_id, tenant_id)
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "message": (
                        "Gemini API quota exceeded or billing required for this model. "
                        "Use another key, enable billing, try a different GEMINI_MODEL, or retry later."
                    ),
                    "request_id": request_id,
                    "type": "llm_quota",
                },
            )
        err_text = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        log.error("chat_crashed request_id=%s tenant_id=%s error=%s", request_id, tenant_id, err_text)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "An internal error occurred. Please try again later.",
                "request_id": request_id,
            },
        )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print("Starting the service on PORT:", str(port))
    reload_enabled = str(os.getenv("UVICORN_RELOAD", "1")).strip().lower() in {"1", "true", "yes", "on"}
    uvicorn.run(
        "server.main:app", host="0.0.0.0", port=port, reload=reload_enabled
    )