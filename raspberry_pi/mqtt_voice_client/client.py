"""
Main MQTT Voice Client for Raspberry Pi
"""

import base64
import json
import logging
import time
from typing import Callable, Optional, Dict, Any

import requests


logger = logging.getLogger(__name__)


class VoiceClient:
    """
    MQTT Voice Client for IoT toys.
    
    Provides simple API for voice interactions with the backend service.
    Supports different toy configurations (full voice, TTS-only, STT-only, etc.)
    
    Example:
        client = VoiceClient(
            device_id="rpi-toy-001",
            api_url="https://your-backend.run.app",
        )
        
        # Full voice interaction
        audio_data = client.record_audio(duration=5)
        response = client.send_voice_query_sync(audio_data)
        client.play_audio(base64.b64decode(response['data']['audio_b64']))
    """
    
    def __init__(
        self,
        device_id: str,
        api_url: str,
        api_key: Optional[str] = None,
        language: str = "en-US",
        sample_rate_hz: int = 16000,
        auto_register: bool = True,
    ):
        """
        Initialize Voice Client.
        
        Args:
            device_id: Unique device identifier (e.g., "rpi-toy-001")
            api_url: Backend API URL (e.g., "https://api.example.com")
            api_key: Optional API key for authentication
            language: Default language code (e.g., "hi-IN", "ta-IN")
            sample_rate_hz: Audio sample rate (16000 recommended)
            auto_register: Automatically register device on first connection
        """
        self.device_id = device_id
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.language = language
        self.sample_rate_hz = sample_rate_hz
        
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-Device-Id": device_id,
        })
        
        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"
        
        self._config: Optional[Dict[str, Any]] = None
        
        if auto_register:
            try:
                self.load_config()
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")
    
    def register_device(
        self,
        domain: str = "education",
        tts_voice: Optional[str] = None,
        tts_provider: str = "qwen",
        capabilities: Optional[Dict[str, bool]] = None,
    ) -> Dict[str, Any]:
        """
        Register device with backend and set configuration.
        
        Args:
            domain: Agent domain (education, wellbeing, etc.)
            tts_voice: Preferred TTS voice (e.g., "indic-hindi-female")
            tts_provider: TTS provider ("qwen" or "elevenlabs")
            capabilities: Device capabilities {"stt": True, "tts": True, "chat": True}
        
        Returns:
            Registration response
        """
        if capabilities is None:
            capabilities = {"stt": True, "tts": True, "chat": True, "streaming": False}
        
        config = {
            "device_id": self.device_id,
            "tenant_id": "tenant-demo",
            "capabilities": capabilities,
            "domain": domain,
            "language": self.language,
            "tts_voice": tts_voice,
            "tts_provider": tts_provider,
            "tts_format": "wav",
            "sample_rate_hz": self.sample_rate_hz,
            "session_timeout_seconds": 3600,
            "custom_settings": {},
        }
        
        response = self.session.post(
            f"{self.api_url}/mqtt/devices/register",
            json=config,
            timeout=10,
        )
        response.raise_for_status()
        
        result = response.json()
        self._config = result.get("data", {})
        logger.info(f"Device registered: {self.device_id}")
        return result
    
    def load_config(self) -> Dict[str, Any]:
        """Load device configuration from backend."""
        response = self.session.get(
            f"{self.api_url}/mqtt/devices/{self.device_id}/config",
            timeout=10,
        )
        
        if response.status_code == 404:
            logger.info(f"Device not registered, registering now: {self.device_id}")
            return self.register_device()
        
        response.raise_for_status()
        self._config = response.json()
        logger.info(f"Config loaded for device: {self.device_id}")
        return self._config
    
    def update_config(self, **kwargs) -> Dict[str, Any]:
        """
        Update device configuration.
        
        Args:
            **kwargs: Config fields to update (language, tts_voice, domain, etc.)
        
        Returns:
            Updated configuration
        """
        config = self._config or self.load_config()
        config.update(kwargs)
        
        response = self.session.put(
            f"{self.api_url}/mqtt/devices/{self.device_id}/config",
            json=config,
            timeout=10,
        )
        response.raise_for_status()
        
        result = response.json()
        self._config = result.get("data", {})
        logger.info(f"Config updated for device: {self.device_id}")
        return result
    
    def send_voice_query_sync(
        self,
        audio_bytes: bytes,
        session_id: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send voice query (synchronous).
        
        Full flow: STT → Chat → TTS
        
        Args:
            audio_bytes: PCM16 mono audio data
            session_id: Optional session ID for conversation context
            language: Override default language
        
        Returns:
            Response dict with transcript, response_text, audio_b64
        """
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        
        payload = {
            "audio_b64": audio_b64,
            "sample_rate_hz": self.sample_rate_hz,
            "session_id": session_id,
            "language": language or self.language,
            "enable_streaming": False,
        }
        
        response = self.session.post(
            f"{self.api_url}/mqtt/devices/{self.device_id}/voice/query",
            json=payload,
            timeout=30,  # Allow time for STT + LLM + TTS
        )
        response.raise_for_status()
        
        result = response.json()
        if not result.get("success"):
            raise RuntimeError(f"Voice query failed: {result.get('error')}")
        
        return result
    
    def send_text_query_sync(
        self,
        text: str,
        session_id: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send text query (synchronous).
        
        Flow: Chat → TTS
        
        Args:
            text: Text query
            session_id: Optional session ID for conversation context
            language: Override default language
        
        Returns:
            Response dict with response_text, audio_b64
        """
        payload = {
            "text": text,
            "session_id": session_id,
            "language": language or self.language,
            "enable_streaming": False,
        }
        
        response = self.session.post(
            f"{self.api_url}/mqtt/devices/{self.device_id}/text/query",
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        
        result = response.json()
        if not result.get("success"):
            raise RuntimeError(f"Text query failed: {result.get('error')}")
        
        return result
    
    def transcribe_audio_sync(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transcribe audio (STT only).
        
        Args:
            audio_bytes: PCM16 mono audio data
            language: Override default language
        
        Returns:
            Response dict with transcript, confidence, language
        """
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        
        payload = {
            "audio_b64": audio_b64,
            "sample_rate_hz": self.sample_rate_hz,
            "language": language or self.language,
        }
        
        response = self.session.post(
            f"{self.api_url}/mqtt/devices/{self.device_id}/transcribe",
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        
        result = response.json()
        if not result.get("success"):
            raise RuntimeError(f"Transcription failed: {result.get('error')}")
        
        return result
    
    def synthesize_speech_sync(
        self,
        text: str,
        language: Optional[str] = None,
        voice: Optional[str] = None,
        format: str = "wav",
    ) -> Dict[str, Any]:
        """
        Synthesize speech (TTS only).
        
        Args:
            text: Text to synthesize
            language: Override default language
            voice: Override default voice
            format: Audio format ("wav" or "mp3")
        
        Returns:
            Response dict with audio_b64, mime_type, voice
        """
        payload = {
            "text": text,
            "language": language or self.language,
            "voice": voice,
            "format": format,
        }
        
        response = self.session.post(
            f"{self.api_url}/mqtt/devices/{self.device_id}/synthesize",
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        
        result = response.json()
        if not result.get("success"):
            raise RuntimeError(f"Synthesis failed: {result.get('error')}")
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════
    # Audio convenience methods (requires audio module)
    # ═══════════════════════════════════════════════════════════════════════
    
    def record_audio(
        self,
        duration: float = 5.0,
        sample_rate: Optional[int] = None,
    ) -> bytes:
        """
        Record audio from microphone.
        
        Args:
            duration: Recording duration in seconds
            sample_rate: Override default sample rate
        
        Returns:
            PCM16 mono audio bytes
        """
        from .audio import AudioRecorder
        
        recorder = AudioRecorder(sample_rate=sample_rate or self.sample_rate_hz)
        return recorder.record(duration=duration)
    
    def play_audio(
        self,
        audio_bytes: bytes,
        sample_rate: Optional[int] = None,
    ) -> None:
        """
        Play audio through speaker.
        
        Args:
            audio_bytes: PCM16 mono audio data
            sample_rate: Override default sample rate
        """
        from .audio import AudioPlayer
        
        player = AudioPlayer(sample_rate=sample_rate or self.sample_rate_hz)
        player.play(audio_bytes)
    
    # ═══════════════════════════════════════════════════════════════════════
    # High-level convenience methods
    # ═══════════════════════════════════════════════════════════════════════
    
    def voice_interaction(
        self,
        duration: float = 5.0,
        play_response: bool = True,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Complete voice interaction: record → query → play response.
        
        Args:
            duration: Recording duration in seconds
            play_response: Automatically play audio response
            session_id: Session ID for conversation context
        
        Returns:
            Full response dict
        """
        logger.info("Recording audio...")
        audio = self.record_audio(duration=duration)
        
        logger.info("Sending voice query...")
        response = self.send_voice_query_sync(audio, session_id=session_id)
        
        if play_response and response.get("data", {}).get("audio_b64"):
            logger.info("Playing response...")
            audio_b64 = response["data"]["audio_b64"]
            self.play_audio(base64.b64decode(audio_b64))
        
        return response
    
    def text_interaction(
        self,
        text: str,
        play_response: bool = True,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Text-based interaction: query → play response.
        
        Args:
            text: Text query
            play_response: Automatically play audio response
            session_id: Session ID for conversation context
        
        Returns:
            Full response dict
        """
        logger.info(f"Sending text query: {text}")
        response = self.send_text_query_sync(text, session_id=session_id)
        
        if play_response and response.get("data", {}).get("audio_b64"):
            logger.info("Playing response...")
            audio_b64 = response["data"]["audio_b64"]
            self.play_audio(base64.b64decode(audio_b64))
        
        return response
    
    def close(self):
        """Close client session."""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
