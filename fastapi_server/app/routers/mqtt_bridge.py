"""
MQTT Bridge Service for IoT Voice Toys

Handles bidirectional MQTT communication between Raspberry Pi devices
and the existing FastAPI backend services (STT, Agent, TTS).

Architecture:
- Receives messages from GCP Pub/Sub (MQTT topics)
- Routes to appropriate service (transcribe, chat, synthesize)
- Publishes responses back to device-specific topics
- Maintains device configuration and session state
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import uuid
import wave
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, field_validator

from app.dependencies import get_speech_provider
from app.providers.speech_provider import SpeechProvider
from app.schemas.agent import AgentAudioInput, AgentDomain, AgentStreamRequest
from app.schemas.interaction import NormalizedInteractionInput
from app.services.bot_gateway_client import open_bot_stream_post
from app.services.input_router import input_router
from app.services.sse_assembler import SSEAssembler
from app.services.sentence_buffer_service import (
    DEFAULT_MAX_CHUNK_WORDS,
    QWEN_MAX_CHUNK_WORDS,
    sentence_buffer_service,
)
from app.services.voice_text_normalizer import voice_text_normalizer
from app.core.agent_routing import resolve_agent_domain_for_routing

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mqtt", tags=["mqtt"])


# ═══════════════════════════════════════════════════════════════════════════
# Models
# ═══════════════════════════════════════════════════════════════════════════


class DeviceCapabilities(BaseModel):
    """What the device can do."""
    stt: bool = True
    tts: bool = True
    chat: bool = True
    streaming: bool = False


class DeviceConfig(BaseModel):
    """Per-device configuration stored in Redis/Firestore."""
    device_id: str = Field(..., min_length=1, max_length=128)
    user_id: str | None = None
    tenant_id: str = "tenant-demo"
    capabilities: DeviceCapabilities = Field(default_factory=DeviceCapabilities)
    domain: str = "education"
    language: str = "en-US"
    tts_voice: str | None = None
    tts_provider: str = "qwen"
    tts_format: str | None = "wav"
    sample_rate_hz: int = 16000
    session_timeout_seconds: int = 3600
    custom_settings: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class MQTTVoiceQuery(BaseModel):
    """Message payload for devices/{device_id}/voice/query"""
    audio_b64: str = Field(..., description="Base64-encoded PCM16 mono audio")
    sample_rate_hz: int | None = None
    session_id: str | None = None
    language: str | None = None
    enable_streaming: bool = False
    
    @field_validator("audio_b64")
    @classmethod
    def validate_audio(cls, value: str) -> str:
        try:
            raw = base64.b64decode(value, validate=True)
            if not raw:
                raise ValueError("Empty audio")
            if len(raw) % 2 != 0:
                raise ValueError("Invalid PCM16 format")
        except Exception as e:
            raise ValueError(f"Invalid audio_b64: {e}") from e
        return value


class MQTTTextQuery(BaseModel):
    """Message payload for devices/{device_id}/text/query"""
    text: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None
    language: str | None = None
    enable_streaming: bool = False


class MQTTTranscribeRequest(BaseModel):
    """Message payload for devices/{device_id}/transcribe"""
    audio_b64: str
    sample_rate_hz: int | None = None
    language: str | None = None


class MQTTSynthesizeRequest(BaseModel):
    """Message payload for devices/{device_id}/synthesize"""
    text: str = Field(..., min_length=1, max_length=5000)
    language: str | None = None
    voice: str | None = None
    format: str | None = None


class MQTTResponse(BaseModel):
    """Generic response envelope"""
    success: bool
    device_id: str
    request_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: dict[str, Any] | None = None
    error: str | None = None


# ═══════════════════════════════════════════════════════════════════════════
# Device Configuration Management
# ═══════════════════════════════════════════════════════════════════════════


class DeviceConfigStore:
    """
    In-memory device config store (prototype).
    TODO: Replace with Redis or Firestore for production.
    """
    
    def __init__(self):
        self._configs: dict[str, DeviceConfig] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, device_id: str) -> DeviceConfig | None:
        """Get device config by ID."""
        async with self._lock:
            return self._configs.get(device_id)
    
    async def get_or_default(self, device_id: str) -> DeviceConfig:
        """Get device config or create default."""
        config = await self.get(device_id)
        if config is None:
            config = DeviceConfig(device_id=device_id)
            await self.set(config)
        return config
    
    async def set(self, config: DeviceConfig) -> None:
        """Save device config."""
        config.updated_at = datetime.utcnow().isoformat()
        async with self._lock:
            self._configs[config.device_id] = config
    
    async def delete(self, device_id: str) -> bool:
        """Delete device config."""
        async with self._lock:
            return self._configs.pop(device_id, None) is not None
    
    async def list_all(self) -> list[DeviceConfig]:
        """List all device configs."""
        async with self._lock:
            return list(self._configs.values())


device_config_store = DeviceConfigStore()


# ═══════════════════════════════════════════════════════════════════════════
# MQTT Message Handlers
# ═══════════════════════════════════════════════════════════════════════════


class MQTTBridgeService:
    """Core MQTT bridge logic."""
    
    def __init__(self):
        self.active_sessions: dict[str, dict] = {}
    
    async def handle_voice_query(
        self,
        device_id: str,
        payload: MQTTVoiceQuery,
        provider: SpeechProvider,
    ) -> MQTTResponse:
        """
        Full voice interaction: STT → Chat → TTS
        
        Flow:
        1. Load device config
        2. Transcribe audio (STT)
        3. Send transcript to agent (Chat)
        4. Synthesize response (TTS)
        5. Return text + audio
        """
        request_id = str(uuid.uuid4())
        config = await device_config_store.get_or_default(device_id)
        
        try:
            # Override with message-level settings
            language = payload.language or config.language
            sample_rate = payload.sample_rate_hz or config.sample_rate_hz
            session_id = payload.session_id or f"mqtt-{device_id}-{int(datetime.utcnow().timestamp())}"
            
            # Step 1: STT
            if not config.capabilities.stt:
                return MQTTResponse(
                    success=False,
                    device_id=device_id,
                    request_id=request_id,
                    error="Device does not support STT",
                )
            
            raw_pcm = base64.b64decode(payload.audio_b64)
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(raw_pcm)
            
            transcript = await provider.transcribe_wav(
                wav_bytes=buf.getvalue(),
                sample_rate_hz=sample_rate,
                language=language,
                request_id=request_id,
            )
            
            transcript_text = (transcript.text or "").strip()
            if not transcript_text:
                return MQTTResponse(
                    success=False,
                    device_id=device_id,
                    request_id=request_id,
                    error="No speech detected",
                )
            
            # Step 2: Chat
            if not config.capabilities.chat:
                # STT-only device
                return MQTTResponse(
                    success=True,
                    device_id=device_id,
                    request_id=request_id,
                    data={
                        "transcript": transcript_text,
                        "confidence": transcript.confidence,
                        "language": transcript.language,
                    },
                )
            
            # Build agent request
            agent_request = AgentStreamRequest(
                session_id=session_id,
                input_type="text",
                text=transcript_text,
                domain=AgentDomain(config.domain) if config.domain else None,
                language=language,
                use_knowledge=True,
                knowledge_top_k=3,
                output_audio=False,  # We'll synthesize separately
            )
            
            # Normalize input
            interaction, route_meta = await input_router.normalize(agent_request, provider)
            if interaction is None:
                return MQTTResponse(
                    success=False,
                    device_id=device_id,
                    request_id=request_id,
                    error="Failed to normalize input",
                    data=route_meta,
                )
            
            # Route to domain bot
            domain_key = resolve_agent_domain_for_routing(config.tenant_id, config.domain)
            if not domain_key:
                return MQTTResponse(
                    success=False,
                    device_id=device_id,
                    request_id=request_id,
                    error="Domain not resolved",
                )
            
            json_body = {
                "query": transcript_text,
                "session_id": session_id,
                "use_knowledge": True,
                "knowledge_top_k": 3,
                "input_type": "text",
                "language": language,
            }
            
            # Get agent response
            media_type, stream = await open_bot_stream_post(
                domain_key=domain_key,
                json_body=json_body,
                tenant_id=config.tenant_id,
                request_id=request_id,
            )
            
            # Collect full response text
            sse = SSEAssembler()
            response_text = ""
            async for chunk in stream:
                for ev, data in sse.feed(chunk):
                    if ev in ("text", "token", "delta"):
                        try:
                            parsed = json.loads(data)
                            piece = parsed if isinstance(parsed, str) else str(
                                parsed.get("text", parsed) if isinstance(parsed, dict) else parsed
                            )
                        except (json.JSONDecodeError, TypeError):
                            piece = data
                        if piece:
                            response_text += piece
            
            # Drain remaining
            for ev, data in sse.drain():
                if ev in ("text", "token", "delta"):
                    try:
                        parsed = json.loads(data)
                        piece = parsed if isinstance(parsed, str) else str(
                            parsed.get("text", parsed) if isinstance(parsed, dict) else parsed
                        )
                    except (json.JSONDecodeError, TypeError):
                        piece = data
                    if piece:
                        response_text += piece
            
            response_text = response_text.strip()
            if not response_text:
                return MQTTResponse(
                    success=False,
                    device_id=device_id,
                    request_id=request_id,
                    error="Empty agent response",
                )
            
            # Step 3: TTS
            if not config.capabilities.tts:
                # Chat-only device
                return MQTTResponse(
                    success=True,
                    device_id=device_id,
                    request_id=request_id,
                    data={
                        "transcript": transcript_text,
                        "response_text": response_text,
                    },
                )
            
            # Normalize text for speech
            speech_text = voice_text_normalizer.normalize(response_text, language) or response_text
            
            audio_bytes, mime, voice_used, tts_req_id = await provider.synthesize_text(
                text=speech_text,
                language=language,
                voice=config.tts_voice,
                emotion=None,
                request_id=request_id,
                output_format=config.tts_format,
                tts_provider=config.tts_provider,
            )
            
            return MQTTResponse(
                success=True,
                device_id=device_id,
                request_id=request_id,
                data={
                    "transcript": transcript_text,
                    "response_text": response_text,
                    "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
                    "mime_type": mime,
                    "voice": voice_used,
                },
            )
        
        except Exception as exc:
            logger.exception("voice_query_failed device_id=%s", device_id)
            return MQTTResponse(
                success=False,
                device_id=device_id,
                request_id=request_id,
                error=f"{type(exc).__name__}: {exc}",
            )
    
    async def handle_text_query(
        self,
        device_id: str,
        payload: MQTTTextQuery,
        provider: SpeechProvider,
    ) -> MQTTResponse:
        """
        Text query: Chat → TTS
        
        For devices with buttons or external text input.
        """
        request_id = str(uuid.uuid4())
        config = await device_config_store.get_or_default(device_id)
        
        try:
            language = payload.language or config.language
            session_id = payload.session_id or f"mqtt-{device_id}-{int(datetime.utcnow().timestamp())}"
            
            if not config.capabilities.chat:
                return MQTTResponse(
                    success=False,
                    device_id=device_id,
                    request_id=request_id,
                    error="Device does not support chat",
                )
            
            # Build agent request
            agent_request = AgentStreamRequest(
                session_id=session_id,
                input_type="text",
                text=payload.text,
                domain=AgentDomain(config.domain) if config.domain else None,
                language=language,
                use_knowledge=True,
                knowledge_top_k=3,
                output_audio=False,
            )
            
            # Normalize input
            interaction, route_meta = await input_router.normalize(agent_request, provider)
            if interaction is None:
                return MQTTResponse(
                    success=False,
                    device_id=device_id,
                    request_id=request_id,
                    error="Failed to normalize input",
                    data=route_meta,
                )
            
            # Route to domain bot
            domain_key = resolve_agent_domain_for_routing(config.tenant_id, config.domain)
            if not domain_key:
                return MQTTResponse(
                    success=False,
                    device_id=device_id,
                    request_id=request_id,
                    error="Domain not resolved",
                )
            
            json_body = {
                "query": payload.text,
                "session_id": session_id,
                "use_knowledge": True,
                "knowledge_top_k": 3,
                "input_type": "text",
                "language": language,
            }
            
            # Get agent response
            media_type, stream = await open_bot_stream_post(
                domain_key=domain_key,
                json_body=json_body,
                tenant_id=config.tenant_id,
                request_id=request_id,
            )
            
            # Collect full response
            sse = SSEAssembler()
            response_text = ""
            async for chunk in stream:
                for ev, data in sse.feed(chunk):
                    if ev in ("text", "token", "delta"):
                        try:
                            parsed = json.loads(data)
                            piece = parsed if isinstance(parsed, str) else str(
                                parsed.get("text", parsed) if isinstance(parsed, dict) else parsed
                            )
                        except (json.JSONDecodeError, TypeError):
                            piece = data
                        if piece:
                            response_text += piece
            
            for ev, data in sse.drain():
                if ev in ("text", "token", "delta"):
                    try:
                        parsed = json.loads(data)
                        piece = parsed if isinstance(parsed, str) else str(
                            parsed.get("text", parsed) if isinstance(parsed, dict) else parsed
                        )
                    except (json.JSONDecodeError, TypeError):
                        piece = data
                    if piece:
                        response_text += piece
            
            response_text = response_text.strip()
            if not response_text:
                return MQTTResponse(
                    success=False,
                    device_id=device_id,
                    request_id=request_id,
                    error="Empty agent response",
                )
            
            # TTS
            if not config.capabilities.tts:
                return MQTTResponse(
                    success=True,
                    device_id=device_id,
                    request_id=request_id,
                    data={"response_text": response_text},
                )
            
            speech_text = voice_text_normalizer.normalize(response_text, language) or response_text
            
            audio_bytes, mime, voice_used, tts_req_id = await provider.synthesize_text(
                text=speech_text,
                language=language,
                voice=config.tts_voice,
                emotion=None,
                request_id=request_id,
                output_format=config.tts_format,
                tts_provider=config.tts_provider,
            )
            
            return MQTTResponse(
                success=True,
                device_id=device_id,
                request_id=request_id,
                data={
                    "response_text": response_text,
                    "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
                    "mime_type": mime,
                    "voice": voice_used,
                },
            )
        
        except Exception as exc:
            logger.exception("text_query_failed device_id=%s", device_id)
            return MQTTResponse(
                success=False,
                device_id=device_id,
                request_id=request_id,
                error=f"{type(exc).__name__}: {exc}",
            )
    
    async def handle_transcribe(
        self,
        device_id: str,
        payload: MQTTTranscribeRequest,
        provider: SpeechProvider,
    ) -> MQTTResponse:
        """STT-only: Audio → Text"""
        request_id = str(uuid.uuid4())
        config = await device_config_store.get_or_default(device_id)
        
        try:
            if not config.capabilities.stt:
                return MQTTResponse(
                    success=False,
                    device_id=device_id,
                    request_id=request_id,
                    error="Device does not support STT",
                )
            
            language = payload.language or config.language
            sample_rate = payload.sample_rate_hz or config.sample_rate_hz
            
            raw_pcm = base64.b64decode(payload.audio_b64)
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(raw_pcm)
            
            transcript = await provider.transcribe_wav(
                wav_bytes=buf.getvalue(),
                sample_rate_hz=sample_rate,
                language=language,
                request_id=request_id,
            )
            
            return MQTTResponse(
                success=True,
                device_id=device_id,
                request_id=request_id,
                data={
                    "transcript": transcript.text,
                    "confidence": transcript.confidence,
                    "language": transcript.language,
                },
            )
        
        except Exception as exc:
            logger.exception("transcribe_failed device_id=%s", device_id)
            return MQTTResponse(
                success=False,
                device_id=device_id,
                request_id=request_id,
                error=f"{type(exc).__name__}: {exc}",
            )
    
    async def handle_synthesize(
        self,
        device_id: str,
        payload: MQTTSynthesizeRequest,
        provider: SpeechProvider,
    ) -> MQTTResponse:
        """TTS-only: Text → Audio"""
        request_id = str(uuid.uuid4())
        config = await device_config_store.get_or_default(device_id)
        
        try:
            if not config.capabilities.tts:
                return MQTTResponse(
                    success=False,
                    device_id=device_id,
                    request_id=request_id,
                    error="Device does not support TTS",
                )
            
            language = payload.language or config.language
            voice = payload.voice or config.tts_voice
            format_ = payload.format or config.tts_format
            
            speech_text = voice_text_normalizer.normalize(payload.text, language) or payload.text
            
            audio_bytes, mime, voice_used, tts_req_id = await provider.synthesize_text(
                text=speech_text,
                language=language,
                voice=voice,
                emotion=None,
                request_id=request_id,
                output_format=format_,
                tts_provider=config.tts_provider,
            )
            
            return MQTTResponse(
                success=True,
                device_id=device_id,
                request_id=request_id,
                data={
                    "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
                    "mime_type": mime,
                    "voice": voice_used,
                },
            )
        
        except Exception as exc:
            logger.exception("synthesize_failed device_id=%s", device_id)
            return MQTTResponse(
                success=False,
                device_id=device_id,
                request_id=request_id,
                error=f"{type(exc).__name__}: {exc}",
            )


mqtt_bridge = MQTTBridgeService()


# ═══════════════════════════════════════════════════════════════════════════
# HTTP Endpoints (for testing and webhook integration)
# ═══════════════════════════════════════════════════════════════════════════


@router.post("/devices/{device_id}/voice/query")
async def mqtt_voice_query(
    device_id: str,
    payload: MQTTVoiceQuery,
    provider: SpeechProvider = Depends(get_speech_provider),
) -> MQTTResponse:
    """
    Full voice interaction: STT → Chat → TTS
    
    For testing, this is an HTTP endpoint. In production, messages arrive via
    GCP Pub/Sub subscriptions.
    """
    return await mqtt_bridge.handle_voice_query(device_id, payload, provider)


@router.post("/devices/{device_id}/text/query")
async def mqtt_text_query(
    device_id: str,
    payload: MQTTTextQuery,
    provider: SpeechProvider = Depends(get_speech_provider),
) -> MQTTResponse:
    """Text query: Chat → TTS"""
    return await mqtt_bridge.handle_text_query(device_id, payload, provider)


@router.post("/devices/{device_id}/transcribe")
async def mqtt_transcribe(
    device_id: str,
    payload: MQTTTranscribeRequest,
    provider: SpeechProvider = Depends(get_speech_provider),
) -> MQTTResponse:
    """STT-only: Audio → Text"""
    return await mqtt_bridge.handle_transcribe(device_id, payload, provider)


@router.post("/devices/{device_id}/synthesize")
async def mqtt_synthesize(
    device_id: str,
    payload: MQTTSynthesizeRequest,
    provider: SpeechProvider = Depends(get_speech_provider),
) -> MQTTResponse:
    """TTS-only: Text → Audio"""
    return await mqtt_bridge.handle_synthesize(device_id, payload, provider)


# ═══════════════════════════════════════════════════════════════════════════
# Device Management Endpoints
# ═══════════════════════════════════════════════════════════════════════════


@router.post("/devices/register")
async def register_device(config: DeviceConfig) -> MQTTResponse:
    """Register a new device or update existing config."""
    try:
        await device_config_store.set(config)
        return MQTTResponse(
            success=True,
            device_id=config.device_id,
            request_id=str(uuid.uuid4()),
            data=config.model_dump(),
        )
    except Exception as exc:
        logger.exception("register_device_failed device_id=%s", config.device_id)
        return MQTTResponse(
            success=False,
            device_id=config.device_id,
            request_id=str(uuid.uuid4()),
            error=str(exc),
        )


@router.get("/devices/{device_id}/config")
async def get_device_config(device_id: str) -> DeviceConfig:
    """Get device configuration."""
    config = await device_config_store.get(device_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return config


@router.put("/devices/{device_id}/config")
async def update_device_config(device_id: str, config: DeviceConfig) -> MQTTResponse:
    """Update device configuration."""
    if config.device_id != device_id:
        raise HTTPException(status_code=400, detail="device_id mismatch")
    
    existing = await device_config_store.get(device_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Device not found")
    
    try:
        await device_config_store.set(config)
        return MQTTResponse(
            success=True,
            device_id=device_id,
            request_id=str(uuid.uuid4()),
            data=config.model_dump(),
        )
    except Exception as exc:
        logger.exception("update_device_config_failed device_id=%s", device_id)
        return MQTTResponse(
            success=False,
            device_id=device_id,
            request_id=str(uuid.uuid4()),
            error=str(exc),
        )


@router.delete("/devices/{device_id}")
async def delete_device(device_id: str) -> MQTTResponse:
    """Delete device and its configuration."""
    deleted = await device_config_store.delete(device_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return MQTTResponse(
        success=True,
        device_id=device_id,
        request_id=str(uuid.uuid4()),
        data={"message": "Device deleted"},
    )


@router.get("/devices")
async def list_devices() -> dict[str, Any]:
    """List all registered devices."""
    configs = await device_config_store.list_all()
    return {
        "devices": [c.model_dump() for c in configs],
        "count": len(configs),
    }
