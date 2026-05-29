from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
import uuid
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.core.agent_routing import resolve_agent_domain_for_routing
from app.dependencies import get_speech_provider, get_tenant_id
from app.providers.speech_provider import SpeechProvider
from app.schemas.agent import AgentAudioInput, AgentDomain, AgentStreamRequest
from app.schemas.interaction import NormalizedInteractionInput
from app.services.bot_gateway_client import UpstreamBotHttpError, open_bot_stream_post
from app.services.input_router import input_router
from app.services.sentence_buffer_service import (
    DEFAULT_MAX_CHUNK_WORDS,
    QWEN_MAX_CHUNK_WORDS,
    QWEN_FIRST_CHUNK_WORDS,
    sentence_buffer_service,
)
from app.services.sse_assembler import SSEAssembler
from app.services.voice_text_normalizer import voice_text_normalizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


def _validate_tenant_id(tenant_id: str | None) -> str:
    value = (tenant_id or "").strip()
    if not value:
        raise ValueError("Missing X-Tenant-Id header")
    if len(value) > 64:
        raise ValueError("X-Tenant-Id must be <= 64 characters")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", value):
        raise ValueError("X-Tenant-Id contains invalid characters")
    return value


async def _emit_json(websocket: WebSocket, event: str, data: dict | str) -> None:
    await websocket.send_json({"event": event, "data": data})


def _bot_json_payload(body: AgentStreamRequest, interaction: NormalizedInteractionInput) -> dict[str, Any]:
    text = (interaction.normalized_text or "").strip()
    out: dict[str, Any] = {
        "query": text,
        "session_id": body.session_id,
        "use_knowledge": body.use_knowledge,
        "knowledge_top_k": body.knowledge_top_k,
        "input_type": interaction.input_type or "text",
        "language": body.language or "en-US",
    }
    if body.access_level is not None:
        out["access_level"] = body.access_level
    if body.provider:
        out["provider"] = body.provider
    if body.llm_model:
        out["llm_model"] = body.llm_model
    if body.history is not None:
        out["history"] = body.history
    return out


def _maybe_json(data: str) -> Any:
    data = data.strip()
    if not data:
        return ""
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return data


@router.post("/stream")
async def stream_agent(
    request: Request,
    body: AgentStreamRequest,
    tenant_id: str = Depends(get_tenant_id),
    provider: SpeechProvider = Depends(get_speech_provider),
):
    """
    Thin proxy: normalize input (STT if needed), then stream the domain bot HTTP body
    as chunks arrive (no full-body buffering on the gateway).
    """
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())

    try:
        interaction, route_meta = await input_router.normalize(body, provider)
    except Exception as exc:
        logger.info("input_router_failed request_id=%s detail=%s", request_id, exc)

        async def err_simple():
            yield f"event: done\ndata: {json.dumps({'ok': False, 'error': 'input_normalization_failed', 'detail': str(exc)}, ensure_ascii=True)}\n\n".encode()

        return StreamingResponse(err_simple(), media_type="text/event-stream")

    if interaction is None:

        async def early():
            yield f"event: input\ndata: {json.dumps(route_meta, ensure_ascii=True)}\n\n".encode()
            yield f"event: done\ndata: {json.dumps({'ok': False, **route_meta}, ensure_ascii=True)}\n\n".encode()

        return StreamingResponse(early(), media_type="text/event-stream")

    explicit = body.domain.value if body.domain is not None else None
    domain_key = resolve_agent_domain_for_routing(tenant_id, explicit)
    if not domain_key:
        msg = {
            "ok": False,
            "error": "domain_not_resolved",
            "detail": "Set a valid `domain` on the request or use an X-Tenant-Id that maps to a domain.",
        }

        async def dom_err():
            yield f"event: status\ndata: {json.dumps(msg, ensure_ascii=True)}\n\n".encode()
            yield f"event: done\ndata: {json.dumps(msg, ensure_ascii=True)}\n\n".encode()

        return StreamingResponse(dom_err(), media_type="text/event-stream")

    logger.info(
        "stream_proxy_start request_id=%s tenant_id=%s domain_key=%s",
        request_id,
        tenant_id,
        domain_key,
    )

    json_body = _bot_json_payload(body, interaction)

    try:
        media_type, stream = await open_bot_stream_post(
            domain_key=domain_key,
            json_body=json_body,
            tenant_id=tenant_id,
            request_id=request_id,
            request=request,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UpstreamBotHttpError as exc:
        logger.warning(
            "bot_http_error request_id=%s status=%s",
            request_id,
            exc.status_code,
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except httpx.RequestError as exc:
        logger.warning("bot_transport_error request_id=%s detail=%s", request_id, exc)
        raise HTTPException(status_code=502, detail="Domain bot unreachable") from exc

    # If output_audio is requested, intercept the bot's SSE stream, buffer sentences,
    # synthesize TTS per sentence, and emit both text + audio events in real-time.
    # Text events are emitted IMMEDIATELY; TTS runs in parallel and audio events follow.
    if body.output_audio:
        from app.providers.disabled_speech_provider import DisabledSpeechProvider

        if isinstance(provider, DisabledSpeechProvider):
            # No TTS available — fall through to plain proxy
            return StreamingResponse(stream, media_type=media_type)

        async def tts_stream():
            sse = SSEAssembler()
            text_buffer = ""
            audio_idx = 0
            full_text_parts: list[str] = []
            tts_queue: asyncio.Queue[str | None] = asyncio.Queue()
            audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

            # Emit transcript/input event if available
            if route_meta.get("transcript"):
                yield f"event: input\ndata: {json.dumps(route_meta, ensure_ascii=True)}\n\n".encode()

            async def tts_worker():
                """Background task: reads sentences from tts_queue, normalizes for speech,
                synthesizes with lookahead pre-buffering, puts audio into audio_queue.

                Uses a concurrent pipeline: starts synthesizing chunk N+1 immediately
                after dequeuing it, while chunk N's synthesis is still in-flight.
                When chunk N completes, it's emitted and chunk N+1 continues synthesizing.
                This eliminates audible gaps for slow TTS providers like Qwen3 (5-8s per
                chunk on T4).
                """
                nonlocal audio_idx

                use_stream = (
                    (body.tts_provider or "").strip().lower() == "qwen"
                    and hasattr(provider, "synthesize_text_stream")
                )

                async def _emit_audio(idx: int, text: str, audio_bytes: bytes, mime: str):
                    audio_payload = {
                        "index": idx,
                        "text": text,
                        "mime_type": mime,
                        "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
                    }
                    return f"event: audio\ndata: {json.dumps(audio_payload, ensure_ascii=True)}\n\n".encode()

                async def _synthesize_one(text: str, idx: int):
                    """Synthesize a single normalized sentence (non-streaming).
                    Returns SSE-encoded audio event bytes or None on failure.
                    """
                    try:
                        audio_bytes, mime, voice_used, tts_req_id = await provider.synthesize_text(
                            text=text,
                            language=body.language,
                            voice=body.tts_voice,
                            emotion=body.tts_emotion,
                            request_id=None,
                            output_format=body.tts_format,
                            tts_provider=body.tts_provider,
                        )
                        return await _emit_audio(idx, text, audio_bytes, mime)
                    except Exception as tts_exc:
                        logger.warning("tts_chunk_failed request_id=%s err=%s", request_id, tts_exc)
                        return None

                # ---- Realtime streaming path (Qwen) --------------------------
                # Process sentences STRICTLY in order. For each sentence, stream
                # its ~1s WAV windows as the GPU renders them and emit each as an
                # audio event immediately. Because we never run two sentences
                # concurrently and the windows are yielded in generation order,
                # the audio_idx is strictly increasing and playback stays in
                # order — no interleaving, no shuffling.
                if use_stream:
                    while True:
                        sentence = await tts_queue.get()
                        if sentence is None:
                            break
                        speech_text = voice_text_normalizer.normalize_sentence(sentence)
                        if not speech_text:
                            continue
                        try:
                            async for win_bytes, win_mime in provider.synthesize_text_stream(
                                text=speech_text,
                                language=body.language,
                                voice=body.tts_voice,
                                request_id=None,
                                tts_provider=body.tts_provider,
                            ):
                                idx = audio_idx
                                audio_idx += 1
                                await audio_queue.put(
                                    await _emit_audio(idx, speech_text, win_bytes, win_mime)
                                )
                        except Exception as tts_exc:
                            logger.warning("tts_stream_failed request_id=%s err=%s", request_id, tts_exc)
                    await audio_queue.put(None)
                    return

                # ---- Non-streaming path (ElevenLabs / fallback) --------------
                # Lookahead pre-buffering pipeline.
                # We maintain a deque of in-flight synthesis futures (max 2) so that
                # chunk N+1 is already synthesizing while chunk N is being transmitted.
                from collections import deque
                in_flight: deque[asyncio.Task] = deque()
                MAX_LOOKAHEAD = 2

                while True:
                    sentence = await tts_queue.get()
                    if sentence is None:
                        break

                    # Normalize text for speech (strip markdown, emojis, special chars)
                    speech_text = voice_text_normalizer.normalize_sentence(sentence)
                    if not speech_text:
                        continue

                    # Assign index now to preserve SSE event ordering
                    idx = audio_idx
                    audio_idx += 1

                    # Start synthesis immediately (non-blocking)
                    in_flight.append(asyncio.ensure_future(_synthesize_one(speech_text, idx)))

                    # If we've hit the lookahead limit, await the oldest task and emit it.
                    # This ensures at most MAX_LOOKAHEAD syntheses run concurrently.
                    if len(in_flight) >= MAX_LOOKAHEAD:
                        result = await in_flight.popleft()
                        if result is not None:
                            await audio_queue.put(result)

                # Drain all remaining in-flight synthesis tasks in order
                while in_flight:
                    result = await in_flight.popleft()
                    if result is not None:
                        await audio_queue.put(result)

                await audio_queue.put(None)

            # Start TTS worker in background
            tts_task = asyncio.create_task(tts_worker())

            # Phase 1: Stream text tokens immediately, queue sentences for TTS
            async for chunk in stream:
                for ev, data in sse.feed(chunk):
                    if ev in ("text", "token", "delta"):
                        piece = ""
                        try:
                            parsed = json.loads(data)
                            piece = parsed if isinstance(parsed, str) else str(parsed.get("text", parsed) if isinstance(parsed, dict) else parsed)
                        except (json.JSONDecodeError, TypeError):
                            piece = data
                        if not piece:
                            continue

                        full_text_parts.append(piece)
                        # Emit text IMMEDIATELY
                        yield f"event: text\ndata: {json.dumps(piece, ensure_ascii=True)}\n\n".encode()

                        # Buffer for TTS sentence detection. Self-hosted
                        # Qwen3 has no streaming, so larger chunks reduce
                        # the audible gaps between clips.
                        text_buffer += piece
                        # Buffer for TTS sentence detection. Self-hosted
                        # Qwen3 has no streaming, so larger chunks reduce
                        # the audible gaps between clips. But the FIRST chunk
                        # is kept small so the user hears audio quickly instead
                        # of waiting for a whole 80-word block to render.
                        is_qwen = (body.tts_provider or "").lower() == "qwen"
                        if is_qwen:
                            chunk_words = QWEN_FIRST_CHUNK_WORDS if audio_idx == 0 else QWEN_MAX_CHUNK_WORDS
                        else:
                            chunk_words = DEFAULT_MAX_CHUNK_WORDS
                        ready, text_buffer = sentence_buffer_service.pop_leading_speech_chunks(
                            text_buffer, max_chunk_words=chunk_words
                        )
                        for sentence in ready:
                            await tts_queue.put(sentence)

                        # Drain any ready audio events (non-blocking)
                        while not audio_queue.empty():
                            item = audio_queue.get_nowait()
                            if item is None:
                                break
                            yield item
                    elif ev == "done":
                        pass
                    else:
                        yield f"event: {ev}\ndata: {data}\n\n".encode()

            # Drain remaining SSE buffer
            for ev, data in sse.drain():
                if ev in ("text", "token", "delta"):
                    piece = ""
                    try:
                        parsed = json.loads(data)
                        piece = parsed if isinstance(parsed, str) else str(parsed.get("text", parsed) if isinstance(parsed, dict) else parsed)
                    except (json.JSONDecodeError, TypeError):
                        piece = data
                    if piece:
                        full_text_parts.append(piece)
                        yield f"event: text\ndata: {json.dumps(piece, ensure_ascii=True)}\n\n".encode()
                        text_buffer += piece

            # Queue remaining buffered text for TTS
            if text_buffer.strip():
                remaining = text_buffer.strip()
                if remaining and remaining[-1] not in ".!?":
                    remaining += "."
                await tts_queue.put(remaining)

            # Signal TTS worker to finish
            await tts_queue.put(None)

            # Emit final_text immediately (don't wait for TTS to finish)
            full_text = "".join(full_text_parts).strip()
            if full_text:
                yield f"event: final_text\ndata: {json.dumps(full_text, ensure_ascii=True)}\n\n".encode()

            # Phase 2: Drain remaining audio from TTS worker
            while True:
                item = await audio_queue.get()
                if item is None:
                    break
                yield item

            await tts_task
            yield f"event: done\ndata: {json.dumps({'ok': True, 'request_id': request_id}, ensure_ascii=True)}\n\n".encode()

        return StreamingResponse(tts_stream(), media_type="text/event-stream")

    return StreamingResponse(stream, media_type=media_type)


@router.websocket("/ws")
async def stream_agent_ws(
    websocket: WebSocket,
    provider: SpeechProvider = Depends(get_speech_provider),
):
    await websocket.accept()

    try:
        tenant_id = _validate_tenant_id(
            websocket.headers.get("x-tenant-id") or websocket.query_params.get("tenant_id")
        )
    except ValueError as exc:
        await _emit_json(websocket, "error", {"reason": str(exc)})
        await websocket.close(code=1008)
        return

    session_id = f"voice-{uuid.uuid4()}"
    sample_rate_hz = 16000
    language = "en-US"
    llm_provider = None
    llm_model = None
    use_knowledge = True
    knowledge_top_k = 3
    access_level = None
    output_audio = True
    tts_provider = None
    tts_voice = None
    tts_format = None
    tts_emotion = None
    one_shot_http_audio = True
    selected_domain = None

    audio_buffer = bytearray()

    async def process_turn() -> None:
        nonlocal audio_buffer

        if not audio_buffer:
            await _emit_json(websocket, "done", {"ok": False, "reason": "missing_audio"})
            return

        request_id = str(uuid.uuid4())
        request_body = AgentStreamRequest(
            session_id=session_id,
            input_type="audio",
            audio=AgentAudioInput(
                audio_b64=base64.b64encode(bytes(audio_buffer)).decode("ascii"),
                sample_rate_hz=sample_rate_hz,
                transport="http",
            ),
            domain=selected_domain,
            one_shot_http_audio=one_shot_http_audio,
            language=language,
            provider=llm_provider,
            llm_model=llm_model,
            use_knowledge=use_knowledge,
            knowledge_top_k=knowledge_top_k,
            access_level=access_level,
            output_audio=output_audio,
            tts_provider=tts_provider,
            tts_voice=tts_voice,
            tts_format=tts_format,
            tts_emotion=tts_emotion,
        )

        interaction, route_meta = await input_router.normalize(request_body, provider)
        await _emit_json(websocket, "input", route_meta)

        if interaction is None:
            await _emit_json(websocket, "done", {"ok": False, **route_meta})
            audio_buffer = bytearray()
            return

        explicit = request_body.domain.value if request_body.domain is not None else None
        domain_key = resolve_agent_domain_for_routing(tenant_id, explicit)
        if not domain_key:
            await _emit_json(
                websocket,
                "done",
                {
                    "ok": False,
                    "error": "domain_not_resolved",
                    "detail": "Set `domain` in the start message or use a tenant id that maps to a domain.",
                },
            )
            audio_buffer = bytearray()
            return

        json_body = _bot_json_payload(request_body, interaction)
        try:
            media_type, stream = await open_bot_stream_post(
                domain_key=domain_key,
                json_body=json_body,
                tenant_id=tenant_id,
                request_id=request_id,
            )
        except KeyError as exc:
            await _emit_json(websocket, "done", {"ok": False, "error": "routing", "detail": str(exc)})
            audio_buffer = bytearray()
            return
        except UpstreamBotHttpError as exc:
            await _emit_json(
                websocket,
                "done",
                {
                    "ok": False,
                    "error": "bot_http",
                    "status": exc.status_code,
                    "detail": exc.detail,
                },
            )
            audio_buffer = bytearray()
            return
        except httpx.RequestError as exc:
            await _emit_json(websocket, "done", {"ok": False, "error": "bot_transport", "detail": str(exc)})
            audio_buffer = bytearray()
            return

        mt_lower = (media_type or "").lower()
        is_sse = "text/event-stream" in mt_lower

        raw = bytearray()
        sse = SSEAssembler()
        tts_tail = ""
        audio_idx = 0
        tts_enabled = bool(output_audio)
        tts_error: str | None = None

        async def _tts_push(text_piece: str) -> None:
            nonlocal tts_tail, tts_enabled, audio_idx, tts_error
            if not tts_enabled or not text_piece:
                return
            tts_tail += text_piece
            is_qwen = (tts_provider or "").lower() == "qwen"
            if is_qwen:
                chunk_words = QWEN_FIRST_CHUNK_WORDS if audio_idx == 0 else QWEN_MAX_CHUNK_WORDS
            else:
                chunk_words = DEFAULT_MAX_CHUNK_WORDS
            ready, tts_tail = sentence_buffer_service.pop_leading_speech_chunks(
                tts_tail, max_chunk_words=chunk_words
            )
            for chunk in ready:
                # Normalize text for natural speech output
                speech_chunk = voice_text_normalizer.normalize_sentence(chunk)
                if not speech_chunk:
                    continue
                try:
                    audio_bytes, mime, voice_used, tts_req_id = await provider.synthesize_text(
                        text=speech_chunk,
                        language=language,
                        voice=tts_voice,
                        emotion=tts_emotion,
                        request_id=None,
                        output_format=tts_format,
                        tts_provider=tts_provider,
                    )
                except Exception as exc:
                    tts_enabled = False
                    tts_error = str(exc)
                    await _emit_json(
                        websocket,
                        "status",
                        "Voice output unavailable right now. Continuing with text response.",
                    )
                    return

                await _emit_json(
                    websocket,
                    "audio",
                    {
                        "index": audio_idx,
                        "text": chunk,
                        "request_id": tts_req_id,
                        "voice": voice_used,
                        "mime_type": mime,
                        "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
                    },
                )
                audio_idx += 1
                await asyncio.sleep(0)

        try:
            async for chunk in stream:
                raw.extend(chunk)
                if is_sse:
                    for ev, data in sse.feed(chunk):
                        await _emit_json(websocket, ev, _maybe_json(data))
                        if ev in ("text", "token", "delta") and isinstance(data, str):
                            await _tts_push(data)
                        elif ev in ("text", "token", "delta"):
                            await _tts_push(json.dumps(data, ensure_ascii=True))
        finally:
            pass

        if is_sse:
            for ev, data in sse.drain():
                await _emit_json(websocket, ev, _maybe_json(data))
                if ev in ("text", "token", "delta") and isinstance(data, str):
                    await _tts_push(data)

            await _emit_json(
                websocket,
                "done",
                {"ok": True, "tts_error": tts_error},
            )
            audio_buffer = bytearray()
            return

        # Non-SSE (e.g. application/json): parse full body
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            await _emit_json(
                websocket,
                "done",
                {"ok": False, "error": "invalid_bot_payload", "detail": "expected JSON object"},
            )
            audio_buffer = bytearray()
            return

        text_out = (payload.get("response") or "").strip()
        if not text_out:
            await _emit_json(websocket, "done", {"ok": False, "error": "empty_bot_response"})
            audio_buffer = bytearray()
            return

        await _emit_json(websocket, "final_text", text_out)

        if output_audio and tts_enabled:
            chunk_words = (
                QWEN_MAX_CHUNK_WORDS
                if (tts_provider or "").lower() == "qwen"
                else DEFAULT_MAX_CHUNK_WORDS
            )
            for chunk in sentence_buffer_service.split_for_tts(text_out, max_chunk_words=chunk_words):
                speech_chunk = voice_text_normalizer.normalize_sentence(chunk)
                if not speech_chunk:
                    continue
                try:
                    audio_bytes, mime, voice_used, tts_req_id = await provider.synthesize_text(
                        text=speech_chunk,
                        language=language,
                        voice=tts_voice,
                        emotion=tts_emotion,
                        request_id=None,
                        output_format=tts_format,
                        tts_provider=tts_provider,
                    )
                except Exception as exc:
                    tts_error = str(exc)
                    break
                await _emit_json(
                    websocket,
                    "audio",
                    {
                        "index": audio_idx,
                        "text": chunk,
                        "request_id": tts_req_id,
                        "voice": voice_used,
                        "mime_type": mime,
                        "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
                    },
                )
                audio_idx += 1
                await asyncio.sleep(0)

        await _emit_json(
            websocket,
            "done",
            {"ok": True, "request_id": payload.get("request_id"), "tts_error": tts_error},
        )
        audio_buffer = bytearray()

    await _emit_json(websocket, "ready", {"session_id": session_id})

    try:
        while True:
            msg = await websocket.receive_json()
            msg_type = str(msg.get("type") or "").strip().lower()

            if msg_type == "start":
                session_id = str(msg.get("session_id") or session_id)
                sample_rate_hz = int(msg.get("sample_rate_hz") or sample_rate_hz)
                language = str(msg.get("language") or language)
                incoming_domain = str(msg.get("domain") or "").strip().lower()
                routed = resolve_agent_domain_for_routing(
                    tenant_id,
                    incoming_domain if incoming_domain else None,
                )
                selected_domain = None
                if routed:
                    try:
                        selected_domain = AgentDomain(routed)
                    except ValueError:
                        selected_domain = None
                llm_provider = msg.get("provider")
                llm_model = msg.get("llm_model")
                use_knowledge = bool(msg.get("use_knowledge", use_knowledge))
                knowledge_top_k = int(msg.get("knowledge_top_k") or knowledge_top_k)
                access_level = msg.get("access_level")
                output_audio = bool(msg.get("output_audio", output_audio))
                tts_voice = msg.get("tts_voice")
                tts_provider = msg.get("tts_provider")
                tts_format = msg.get("tts_format")
                tts_emotion = msg.get("tts_emotion")
                one_shot_http_audio = bool(msg.get("one_shot_http_audio", one_shot_http_audio))

                audio_buffer = bytearray()
                await _emit_json(websocket, "started", {"session_id": session_id})
                continue

            if msg_type == "audio_chunk":
                audio_b64 = str(msg.get("audio_b64") or "")
                if not audio_b64:
                    await _emit_json(websocket, "error", {"reason": "missing_audio_chunk"})
                    continue

                try:
                    raw_chunk = base64.b64decode(audio_b64, validate=True)
                except Exception:
                    await _emit_json(websocket, "error", {"reason": "invalid_audio_chunk_base64"})
                    continue

                if not raw_chunk or len(raw_chunk) % 2 != 0:
                    await _emit_json(websocket, "error", {"reason": "invalid_pcm16_chunk"})
                    continue

                audio_buffer.extend(raw_chunk)
                buffered_ms = int((len(audio_buffer) / 2.0) / max(sample_rate_hz, 1) * 1000)
                await _emit_json(
                    websocket,
                    "audio_progress",
                    {
                        "buffered_ms": buffered_ms,
                        "buffer_bytes": len(audio_buffer),
                    },
                )
                continue

            if msg_type == "finalize":
                await process_turn()
                continue

            if msg_type == "ping":
                await _emit_json(websocket, "pong", {"ok": True})
                continue

            if msg_type == "stop":
                await _emit_json(websocket, "stopped", {"ok": True})
                break

            await _emit_json(websocket, "error", {"reason": "unsupported_message_type"})

    except WebSocketDisconnect:
        return
    except Exception as exc:
        await _emit_json(websocket, "error", {"reason": str(exc)})
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
