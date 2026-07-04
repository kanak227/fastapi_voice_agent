#!/usr/bin/env python3
"""
Example: TTS-Only Toy (Toy Type B)

Hardware requirements:
- Raspberry Pi (any model with audio)
- Speaker or headphones

This toy supports:
- Text-to-speech only
- No microphone needed
- Can be triggered by buttons, app, or external source

Usage:
    python tts_only_toy.py
    
    Enter text, and the toy will speak it.
"""

import logging
import sys

sys.path.insert(0, "../mqtt_voice_client")

from mqtt_voice_client import VoiceClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    # Configuration
    DEVICE_ID = "rpi-tts-only-002"
    API_URL = "https://your-backend.run.app"  # Replace with your backend URL
    LANGUAGE = "ta-IN"  # Tamil
    TTS_VOICE = "indic-tamil-male"
    
    logger.info("Initializing TTS-Only Toy...")
    logger.info(f"Device ID: {DEVICE_ID}")
    logger.info(f"Language: {LANGUAGE}")
    logger.info(f"TTS Voice: {TTS_VOICE}")
    
    # Initialize client
    client = VoiceClient(
        device_id=DEVICE_ID,
        api_url=API_URL,
        language=LANGUAGE,
        sample_rate_hz=16000,
    )
    
    # Register device (TTS-only)
    try:
        client.register_device(
            domain="education",
            tts_voice=TTS_VOICE,
            tts_provider="qwen",
            capabilities={
                "stt": False,  # No microphone
                "tts": True,   # Speaker only
                "chat": False, # No LLM
                "streaming": False,
            },
        )
        logger.info("Device registered successfully!")
    except Exception as e:
        logger.warning(f"Registration failed (may already exist): {e}")
    
    logger.info("\n" + "="*60)
    logger.info("TTS-Only Toy Ready!")
    logger.info("="*60)
    logger.info("Enter text to speak (Tamil)")
    logger.info("Ctrl+C to exit")
    logger.info("="*60 + "\n")
    
    try:
        while True:
            # Get text input
            text = input("\nEnter text to speak: ").strip()
            
            if not text:
                continue
            
            print("🔄 Synthesizing speech...")
            
            # Synthesize speech
            response = client.synthesize_speech_sync(text)
            
            if response.get("success"):
                data = response.get("data", {})
                
                print(f"✓ Synthesized: {text}")
                print(f"🎵 Voice: {data.get('voice', 'unknown')}")
                
                # Play audio
                if data.get("audio_b64"):
                    print("🔊 Playing audio...")
                    import base64
                    audio_bytes = base64.b64decode(data["audio_b64"])
                    client.play_audio(audio_bytes)
                    print("✓ Audio finished")
                else:
                    print("⚠️  No audio in response")
            else:
                error = response.get("error", "Unknown error")
                print(f"❌ Error: {error}")
    
    except KeyboardInterrupt:
        logger.info("\n\nShutting down...")
    finally:
        client.close()
        logger.info("Goodbye!")


if __name__ == "__main__":
    main()
