#!/usr/bin/env python3
"""
Example: Full Voice Toy (Toy Type A)

Hardware requirements:
- Raspberry Pi (any model with audio)
- USB microphone or I2S microphone
- Speaker or headphones

This toy supports:
- Voice input (STT)
- Chat/conversation (LLM)
- Voice output (TTS)

Usage:
    python full_voice_toy.py
    
    Press Enter to start recording, speak for 5 seconds.
    The toy will transcribe, get a chat response, and speak it back.
"""

import logging
import sys
import time

# Add parent directory to path to import mqtt_voice_client
sys.path.insert(0, "../mqtt_voice_client")

from mqtt_voice_client import VoiceClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    # Configuration
    DEVICE_ID = "rpi-full-voice-001"
    API_URL = "https://your-backend.run.app"  # Replace with your backend URL
    LANGUAGE = "hi-IN"  # Hindi
    TTS_VOICE = "indic-hindi-female"
    DOMAIN = "education"
    
    logger.info("Initializing Full Voice Toy...")
    logger.info(f"Device ID: {DEVICE_ID}")
    logger.info(f"Language: {LANGUAGE}")
    logger.info(f"TTS Voice: {TTS_VOICE}")
    logger.info(f"Domain: {DOMAIN}")
    
    # Initialize client
    client = VoiceClient(
        device_id=DEVICE_ID,
        api_url=API_URL,
        language=LANGUAGE,
        sample_rate_hz=16000,
    )
    
    # Register device (first time only, config is stored on server)
    try:
        client.register_device(
            domain=DOMAIN,
            tts_voice=TTS_VOICE,
            tts_provider="qwen",  # Use self-hosted Qwen for Indian voices
            capabilities={
                "stt": True,
                "tts": True,
                "chat": True,
                "streaming": False,
            },
        )
        logger.info("Device registered successfully!")
    except Exception as e:
        logger.warning(f"Registration failed (may already exist): {e}")
    
    # Generate session ID for conversation context
    session_id = f"session-{int(time.time())}"
    
    logger.info("\n" + "="*60)
    logger.info("Full Voice Toy Ready!")
    logger.info("="*60)
    logger.info("Press Enter to start recording (5 seconds)")
    logger.info("Speak clearly in Hindi")
    logger.info("Ctrl+C to exit")
    logger.info("="*60 + "\n")
    
    try:
        while True:
            # Wait for user input
            input("Press Enter to speak...")
            
            print("\n🎤 Recording... (5 seconds)")
            
            # Record audio
            audio = client.record_audio(duration=5.0)
            print(f"✓ Recorded {len(audio)} bytes")
            
            # Send to backend (STT + Chat + TTS)
            print("🔄 Processing (STT → Chat → TTS)...")
            response = client.send_voice_query_sync(
                audio,
                session_id=session_id,
            )
            
            if response.get("success"):
                data = response.get("data", {})
                
                # Show transcript
                transcript = data.get("transcript", "")
                print(f"\n📝 You said: {transcript}")
                
                # Show response text
                response_text = data.get("response_text", "")
                print(f"💬 Bot says: {response_text}")
                
                # Play audio response
                if data.get("audio_b64"):
                    print("🔊 Playing audio...")
                    import base64
                    audio_bytes = base64.b64decode(data["audio_b64"])
                    client.play_audio(audio_bytes)
                    print("✓ Audio finished\n")
                else:
                    print("⚠️  No audio in response\n")
            else:
                error = response.get("error", "Unknown error")
                print(f"❌ Error: {error}\n")
            
            print("-" * 60 + "\n")
    
    except KeyboardInterrupt:
        logger.info("\n\nShutting down...")
    finally:
        client.close()
        logger.info("Goodbye!")


if __name__ == "__main__":
    main()
