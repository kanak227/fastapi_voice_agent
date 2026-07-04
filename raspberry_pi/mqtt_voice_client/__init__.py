"""
MQTT Voice Client Library for Raspberry Pi IoT Toys

A lightweight Python library for connecting Raspberry Pi devices to the
GCP-based voice chatbot service via MQTT.

Features:
- Full voice interaction (STT + Chat + TTS)
- Text-only chat
- Audio transcription only
- Text-to-speech only
- Automatic reconnection
- Device configuration management
- Audio recording and playback

Usage:
    from mqtt_voice_client import VoiceClient
    
    client = VoiceClient(
        device_id="rpi-toy-001",
        api_url="https://your-backend.run.app",
    )
    
    # Full voice query
    def on_response(response):
        print(f"Text: {response['response_text']}")
        audio_bytes = base64.b64decode(response['audio_b64'])
        client.play_audio(audio_bytes)
    
    audio = client.record_audio(duration=5)
    client.send_voice_query(audio, callback=on_response)
"""

from .client import VoiceClient
from .audio import AudioRecorder, AudioPlayer

__all__ = ["VoiceClient", "AudioRecorder", "AudioPlayer"]
__version__ = "0.1.0"
