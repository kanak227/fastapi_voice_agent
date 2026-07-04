# Raspberry Pi MQTT Voice Client

Python library for connecting Raspberry Pi IoT voice toys to the GCP-based chatbot service.

## Features

- **Full voice interaction**: Speech-to-Text, Chat, Text-to-Speech
- **Flexible configurations**: Supports different toy types (STT-only, TTS-only, button-based, etc.)
- **Multi-language support**: All 16 languages supported by the backend (Hindi, Tamil, Telugu, Bengali, etc.)
- **Multiple audio backends**: sounddevice, pyaudio, or alsaaudio
- **Simple API**: Easy to integrate with various hardware configurations
- **Automatic reconnection**: Robust handling of network issues

## Quick Start

### 1. Installation

```bash
cd raspberry_pi/mqtt_voice_client
pip install -r requirements.txt
```

### 2. Basic Usage

```python
from mqtt_voice_client import VoiceClient

# Initialize client
client = VoiceClient(
    device_id="rpi-toy-001",
    api_url="https://your-backend.run.app",
    language="hi-IN",  # Hindi
)

# Register device
client.register_device(
    domain="education",
    tts_voice="indic-hindi-female",
    tts_provider="qwen",
)

# Full voice interaction
response = client.voice_interaction(
    duration=5.0,        # Record for 5 seconds
    play_response=True,  # Auto-play response
)

print(f"You said: {response['data']['transcript']}")
print(f"Bot replied: {response['data']['response_text']}")
```

## Toy Configurations

### Toy Type A: Full Voice Assistant

Complete voice interaction with STT, Chat, and TTS.

```python
client.register_device(
    domain="education",
    tts_voice="indic-hindi-female",
    capabilities={
        "stt": True,
        "tts": True,
        "chat": True,
    }
)

# Use voice interaction
response = client.voice_interaction(duration=5.0)
```

**Example**: `examples/full_voice_toy.py`

### Toy Type B: TTS-Only (Story Narrator)

Text-to-speech only, no microphone required.

```python
client.register_device(
    domain="education",
    tts_voice="indic-tamil-male",
    capabilities={
        "stt": False,
        "tts": True,
        "chat": False,
    }
)

# Synthesize and play
response = client.synthesize_speech_sync("வணக்கம்! உங்களுக்கு எப்படி உதவ முடியும்?")
```

**Example**: `examples/tts_only_toy.py`

### Toy Type C: STT-Only (Voice Recorder)

Speech-to-text only for transcription.

```python
client.register_device(
    capabilities={
        "stt": True,
        "tts": False,
        "chat": False,
    }
)

# Record and transcribe
audio = client.record_audio(duration=5.0)
response = client.transcribe_audio_sync(audio)
print(f"Transcript: {response['data']['transcript']}")
```

### Toy Type D: Button-Based Toy

Hardware buttons trigger predefined queries with TTS responses.

```python
client.register_device(
    domain="wellbeing",
    tts_voice="indic-english-female",
    capabilities={
        "stt": False,
        "tts": True,
        "chat": True,
    }
)

# Text query with audio response
response = client.text_interaction("Tell me a relaxing story")
```

**Example**: `examples/button_toy.py`

## Supported Languages

All Indian languages supported by the backend:

- Hindi (hi-IN)
- Tamil (ta-IN)
- Telugu (te-IN)
- Bengali (bn-IN)
- Marathi (mr-IN)
- Gujarati (gu-IN)
- Kannada (kn-IN)
- Malayalam (ml-IN)
- Punjabi (pa-IN)
- Odia (or-IN)
- Assamese (as-IN)
- Bodo (brx-IN)
- Manipuri (mni-IN)
- Rajasthani (raj-IN)
- English (en-IN, en-US)

## Available TTS Voices

### AI4Bharat FastPitch Voices (Qwen Provider)

**Format**: `indic-{language}-{gender}`

Examples:
- `indic-hindi-female`, `indic-hindi-male`
- `indic-tamil-female`, `indic-tamil-male`
- `indic-telugu-female`, `indic-telugu-male`
- `indic-bengali-female`, `indic-bengali-male`
- `indic-english-female`, `indic-english-male`

### ElevenLabs Voices (Cloud)

Standard ElevenLabs voice IDs (see `/voice/voices?tts_provider=elevenlabs`)

## Hardware Requirements

### Minimum (TTS-only)
- Raspberry Pi Zero W or higher
- Speaker or 3.5mm audio jack
- 512MB RAM

### Recommended (Full voice)
- Raspberry Pi 3B+ or higher
- USB microphone or I2S microphone
- Speaker or headphones
- 1GB+ RAM

### Audio Options

**Microphone**:
- USB microphone (plug-and-play)
- I2S MEMS microphone (better quality)
- USB webcam with built-in mic

**Speaker**:
- 3.5mm audio jack
- USB speaker
- I2S audio HAT
- Bluetooth speaker

## API Reference

### VoiceClient

```python
client = VoiceClient(
    device_id="rpi-toy-001",
    api_url="https://your-backend.run.app",
    api_key=None,              # Optional
    language="en-US",
    sample_rate_hz=16000,
    auto_register=True,
)
```

### Methods

#### `register_device(domain, tts_voice, tts_provider, capabilities)`
Register device with backend.

#### `load_config()`
Load device configuration from backend.

#### `update_config(**kwargs)`
Update device configuration.

#### `send_voice_query_sync(audio_bytes, session_id, language)`
Full voice interaction (STT + Chat + TTS).

#### `send_text_query_sync(text, session_id, language)`
Text query with TTS response.

#### `transcribe_audio_sync(audio_bytes, language)`
Speech-to-text only.

#### `synthesize_speech_sync(text, language, voice, format)`
Text-to-speech only.

#### `record_audio(duration, sample_rate)`
Record audio from microphone.

#### `play_audio(audio_bytes, sample_rate)`
Play audio through speaker.

#### `voice_interaction(duration, play_response, session_id)`
Complete voice interaction with auto-record and auto-play.

#### `text_interaction(text, play_response, session_id)`
Text query with auto-play response.

## Troubleshooting

### No audio backend available

Install one of the supported audio libraries:

```bash
# Option 1: sounddevice (recommended)
pip install sounddevice numpy

# Option 2: pyaudio
sudo apt-get install portaudio19-dev python3-pyaudio
pip install pyaudio

# Option 3: alsaaudio (Linux only)
sudo apt-get install libasound2-dev
pip install pyalsaaudio
```

### Recording not working

Check microphone:
```bash
arecord -l  # List recording devices
arecord -d 5 test.wav  # Test recording
aplay test.wav  # Test playback
```

Increase microphone volume:
```bash
alsamixer  # Use arrow keys to adjust
```

### Playback not working

Check speaker:
```bash
aplay -l  # List playback devices
speaker-test -t wav -c 2  # Test speakers
```

Set default audio device:
```bash
# Edit ~/.asoundrc
pcm.!default {
    type hw
    card 0
    device 0
}
```

### Network issues

Check connectivity:
```bash
ping your-backend.run.app
curl https://your-backend.run.app/health
```

## Examples

See the `examples/` directory for complete working examples:

- `full_voice_toy.py` - Complete voice interaction
- `tts_only_toy.py` - Text-to-speech narrator
- `button_toy.py` - Hardware button interface

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub or contact support.
