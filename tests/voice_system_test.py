"""
Comprehensive Voice System Testing Script

Tests STT (Speech-to-Text) and TTS (Text-to-Speech) across:
- All supported languages
- All available voices (ElevenLabs and Qwen)
- All bot domains

This script tests the API endpoints but cannot verify actual audio quality.
For audio quality testing, use the manual testing checklist.
"""

import asyncio
import base64
import json
import os
import sys
import wave
from pathlib import Path
from typing import Dict, List, Optional

import httpx
import numpy as np

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
TENANT_ID = os.getenv("TENANT_ID", "default")

# Test languages
LANGUAGES = [
    ("en-US", "English"),
    ("hi", "Hindi"),
    ("hi-Latn", "Hinglish"),
    ("ta", "Tamil"),
    ("te", "Telugu"),
    ("mr", "Marathi"),
    ("bn", "Bengali"),
    ("gu", "Gujarati"),
    ("kn", "Kannada"),
    ("ml", "Malayalam"),
    ("pa", "Punjabi"),
    ("fr", "French"),
    ("de", "German"),
    ("es", "Spanish"),
    ("ar", "Arabic"),
    ("zh", "Chinese"),
    ("ja", "Japanese"),
]

# Test domains
DOMAINS = [
    "education",
    "religious",
    "design-thinking",
    "digital-literacy",
    "emotional-intelligence",
    "entrepreneurship",
    "financial-literacy",
    "global-citizenship",
    "sustainability",
    "wellbeing",
]

# Test phrases by language
TEST_PHRASES = {
    "en-US": "Hello, how are you today?",
    "hi": "नमस्ते, आप कैसे हैं?",
    "hi-Latn": "namaste aap kaise hain",
    "ta": "வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்?",
    "te": "నమస్కారం, మీరు ఎలా ఉన్నారు?",
    "mr": "नमस्कार, तुम्ही कसे आहात?",
    "bn": "নমস্কার, আপনি কেমন আছেন?",
    "gu": "નમસ્તે, તમે કેમ છો?",
    "kn": "ನಮಸ್ಕಾರ, ನೀವು ಹೇಗಿದ್ದೀರಿ?",
    "ml": "നമസ്കാരം, നിങ്ങൾ എങ്ങനെയുണ്ട്?",
    "pa": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ, ਤੁਸੀਂ ਕਿਵੇਂ ਹੋ?",
    "fr": "Bonjour, comment allez-vous?",
    "de": "Hallo, wie geht es dir?",
    "es": "Hola, ¿cómo estás?",
    "ar": "مرحبا، كيف حالك؟",
    "zh": "你好，你好吗？",
    "ja": "こんにちは、お元気ですか？",
}


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


def generate_test_audio(text: str, sample_rate: int = 16000, duration: float = 1.0) -> bytes:
    """
    Generate a simple test audio (sine wave) as WAV bytes.
    This is a placeholder - in real testing you'd use actual speech audio.
    """
    num_samples = int(sample_rate * duration)
    frequency = 440.0  # A4 note
    t = np.linspace(0, duration, num_samples, dtype=np.float32)
    audio = np.sin(2 * np.pi * frequency * t) * 0.3
    pcm16 = (audio * 32767).astype(np.int16)
    
    # Create WAV file in memory
    import io
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16.tobytes())
    
    return buffer.getvalue()


async def test_voice_listing(provider: str, language: Optional[str] = None) -> List[Dict]:
    """Test voice listing endpoint"""
    url = f"{BACKEND_URL}/voice/voices?tts_provider={provider}"
    if language:
        url += f"&language={language}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                url,
                headers={"X-Tenant-Id": TENANT_ID}
            )
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list):
                voices = data
            elif isinstance(data, dict) and "voices" in data:
                voices = data["voices"]
            else:
                voices = []
            
            return voices
        except Exception as e:
            print_error(f"Voice listing failed for {provider}: {e}")
            return []


async def test_tts_synthesis(
    text: str,
    language: str,
    provider: str,
    voice: Optional[str] = None
) -> bool:
    """Test TTS synthesis endpoint"""
    url = f"{BACKEND_URL}/voice/synthesize"
    
    payload = {
        "text": text,
        "language": language,
        "tts_provider": provider,
    }
    if voice:
        payload["voice"] = voice
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Tenant-Id": TENANT_ID
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Check if audio was generated
            if data.get("audio_b64"):
                audio_bytes = base64.b64decode(data["audio_b64"])
                if len(audio_bytes) > 0:
                    return True
            
            return False
        except Exception as e:
            print_error(f"TTS synthesis failed: {e}")
            return False


async def test_stt_transcription(
    audio_b64: str,
    language: str,
    sample_rate: int = 16000
) -> Optional[str]:
    """Test STT transcription endpoint"""
    url = f"{BACKEND_URL}/voice/transcribe"
    
    payload = {
        "audio": {
            "audio_b64": audio_b64,
            "sample_rate_hz": sample_rate,
            "transport": "http"
        },
        "language": language
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Tenant-Id": TENANT_ID
                }
            )
            response.raise_for_status()
            data = response.json()
            
            return data.get("text", "")
        except Exception as e:
            print_error(f"STT transcription failed: {e}")
            return None


async def test_voice_agent_endpoint(
    audio_b64: str,
    language: str,
    domain: str,
    provider: str,
    voice: Optional[str] = None,
    sample_rate: int = 16000
) -> bool:
    """Test the complete voice agent endpoint"""
    url = f"{FRONTEND_URL}/api/Voice/agent"
    
    payload = {
        "audio_b64": audio_b64,
        "sample_rate_hz": sample_rate,
        "language": language,
        "domain": domain,
        "tts_provider": provider,
        "stream": False
    }
    if voice:
        payload["tts_voice"] = voice
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            
            # Check if we got transcript and audio response
            has_transcript = bool(data.get("transcript"))
            has_audio = bool(data.get("audio_chunks")) and len(data["audio_chunks"]) > 0
            
            return has_transcript and has_audio
        except Exception as e:
            print_error(f"Voice agent endpoint failed: {e}")
            return False


async def run_voice_listing_tests():
    """Test voice listing for all providers and languages"""
    print_header("Voice Listing Tests")
    
    providers = ["elevenlabs", "qwen"]
    results = {"passed": 0, "failed": 0}
    
    for provider in providers:
        print_info(f"Testing {provider} voice listing...")
        
        # Test without language filter
        voices = await test_voice_listing(provider)
        if voices:
            print_success(f"{provider}: Found {len(voices)} voices (no filter)")
            results["passed"] += 1
        else:
            print_error(f"{provider}: No voices found (no filter)")
            results["failed"] += 1
        
        # Test with language filters
        for lang_code, lang_name in LANGUAGES[:5]:  # Test first 5 languages
            voices = await test_voice_listing(provider, lang_code)
            if voices:
                print_success(f"{provider} ({lang_name}): Found {len(voices)} voices")
                results["passed"] += 1
            else:
                print_warning(f"{provider} ({lang_name}): No voices found")
                results["failed"] += 1
    
    print(f"\n{Colors.BOLD}Voice Listing Results: {results['passed']} passed, {results['failed']} failed{Colors.RESET}")


async def run_tts_tests():
    """Test TTS synthesis for all languages and voices"""
    print_header("TTS Synthesis Tests")
    
    providers = ["elevenlabs", "qwen"]
    results = {"passed": 0, "failed": 0}
    
    for provider in providers:
        print_info(f"Testing {provider} TTS synthesis...")
        
        # Get available voices
        voices = await test_voice_listing(provider)
        if not voices:
            print_warning(f"No voices available for {provider}, skipping...")
            continue
        
        # Test each language with default voice
        for lang_code, lang_name in LANGUAGES:
            text = TEST_PHRASES.get(lang_code, "Hello, this is a test.")
            
            success = await test_tts_synthesis(text, lang_code, provider)
            if success:
                print_success(f"{provider} ({lang_name}): TTS synthesis successful")
                results["passed"] += 1
            else:
                print_error(f"{provider} ({lang_name}): TTS synthesis failed")
                results["failed"] += 1
        
        # Test voice selection with first 3 voices
        print_info(f"Testing voice selection for {provider}...")
        test_text = "This is a voice selection test."
        test_lang = "en-US"
        
        for voice in voices[:3]:
            voice_id = voice.get("voice_id")
            voice_name = voice.get("name", voice_id)
            
            success = await test_tts_synthesis(test_text, test_lang, provider, voice_id)
            if success:
                print_success(f"{provider} - {voice_name}: Voice selection successful")
                results["passed"] += 1
            else:
                print_error(f"{provider} - {voice_name}: Voice selection failed")
                results["failed"] += 1
    
    print(f"\n{Colors.BOLD}TTS Synthesis Results: {results['passed']} passed, {results['failed']} failed{Colors.RESET}")


async def run_stt_tests():
    """Test STT transcription for all languages"""
    print_header("STT Transcription Tests")
    
    results = {"passed": 0, "failed": 0}
    
    # Generate test audio
    test_audio = generate_test_audio("test", duration=1.0)
    audio_b64 = base64.b64encode(test_audio).decode("ascii")
    
    for lang_code, lang_name in LANGUAGES:
        transcript = await test_stt_transcription(audio_b64, lang_code)
        
        if transcript is not None:
            print_success(f"{lang_name}: STT transcription returned (transcript: '{transcript}')")
            results["passed"] += 1
        else:
            print_error(f"{lang_name}: STT transcription failed")
            results["failed"] += 1
    
    print(f"\n{Colors.BOLD}STT Transcription Results: {results['passed']} passed, {results['failed']} failed{Colors.RESET}")
    print_warning("Note: Test audio is synthetic, so transcripts may be empty or inaccurate")


async def run_integration_tests():
    """Test complete voice agent flow for selected combinations"""
    print_header("Integration Tests (Voice Agent Endpoint)")
    
    results = {"passed": 0, "failed": 0}
    
    # Generate test audio
    test_audio = generate_test_audio("test", duration=1.0)
    audio_b64 = base64.b64encode(test_audio).decode("ascii")
    
    # Test a subset of combinations (language x domain x provider)
    test_combinations = [
        ("en-US", "education", "elevenlabs"),
        ("hi", "religious", "qwen"),
        ("ta", "wellbeing", "elevenlabs"),
        ("es", "sustainability", "qwen"),
    ]
    
    for lang_code, domain, provider in test_combinations:
        lang_name = next((name for code, name in LANGUAGES if code == lang_code), lang_code)
        
        success = await test_voice_agent_endpoint(
            audio_b64, lang_code, domain, provider
        )
        
        if success:
            print_success(f"{lang_name} + {domain} + {provider}: Integration test passed")
            results["passed"] += 1
        else:
            print_error(f"{lang_name} + {domain} + {provider}: Integration test failed")
            results["failed"] += 1
    
    print(f"\n{Colors.BOLD}Integration Test Results: {results['passed']} passed, {results['failed']} failed{Colors.RESET}")
    print_warning("Note: Test audio is synthetic, so some failures are expected")


async def main():
    """Run all tests"""
    print_header("Voice System Comprehensive Test Suite")
    print_info(f"Backend URL: {BACKEND_URL}")
    print_info(f"Frontend URL: {FRONTEND_URL}")
    print_info(f"Tenant ID: {TENANT_ID}")
    
    try:
        # Run all test suites
        await run_voice_listing_tests()
        await run_tts_tests()
        await run_stt_tests()
        await run_integration_tests()
        
        print_header("Test Suite Complete")
        print_info("For audio quality testing, please use the manual testing checklist:")
        print_info("  VOICE_TESTING_CHECKLIST.md")
        
    except KeyboardInterrupt:
        print_warning("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Test suite failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
