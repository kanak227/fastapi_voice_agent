# MQTT IoT Architecture for Raspberry Pi Voice Toys

## Overview

This document describes the architecture for connecting Raspberry Pi-based IoT voice toys to our existing GCP-hosted chatbot service via MQTT. The system provides a flexible, modular approach supporting various toy configurations (STT+TTS, TTS-only, STT-only, custom hardware buttons, etc.).

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Raspberry Pi IoT Devices                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐│
│  │  Toy A     │  │  Toy B     │  │  Toy C     │  │  Toy D     ││
│  │  (Full)    │  │  (TTS-only)│  │  (STT-only)│  │  (Custom)  ││
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘│
└────────┼───────────────┼───────────────┼───────────────┼────────┘
         │               │               │               │
         └───────────────┴───────────────┴───────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   MQTT Broker         │
                    │   (GCP Pub/Sub or     │
                    │    Cloud IoT Core)    │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │  MQTT Bridge Service  │
                    │  (Cloud Run)          │
                    └───────────┬───────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
    ┌────▼─────┐       ┌────────▼────────┐    ┌──────▼──────┐
    │  STT     │       │   Chat/Agent    │    │   TTS       │
    │  Service │       │   Service       │    │   Service   │
    │(Deepgram)│       │(Multi-Bot)      │    │(Qwen/Eleven)│
    └──────────┘       └─────────────────┘    └─────────────┘
         │                      │                      │
         └──────────────────────┴──────────────────────┘
                                │
                     Existing FastAPI Backend
```

## Components

### 1. Raspberry Pi Client Library

**Location**: `raspberry_pi/mqtt_voice_client/`

**Features**:
- Lightweight Python library for RPi devices
- Handles MQTT connection, authentication, reconnection
- Provides simple API for different toy types
- Audio capture/playback abstraction
- Configuration per device (user preferences, voice, language)

**Key Methods**:
```python
# Full voice toy (STT + Chat + TTS)
client.send_voice_query(audio_bytes, callback=on_response)

# TTS-only toy (text to speech)
client.request_speech(text, callback=on_audio)

# STT-only toy (speech to text)
client.transcribe_audio(audio_bytes, callback=on_transcript)

# Button-triggered chat
client.send_text_query(text, callback=on_response)
```

### 2. MQTT Topics Structure

```
# Device to Cloud (Commands)
devices/{device_id}/voice/query          # Audio for STT + Chat + TTS
devices/{device_id}/text/query           # Text for Chat + TTS
devices/{device_id}/transcribe           # Audio for STT only
devices/{device_id}/synthesize           # Text for TTS only
devices/{device_id}/status               # Device health/status
devices/{device_id}/config/request       # Request config update

# Cloud to Device (Responses)
devices/{device_id}/voice/response       # Complete response (text + audio)
devices/{device_id}/text/response        # Text-only response
devices/{device_id}/audio/chunk          # Audio streaming chunks
devices/{device_id}/transcript           # STT result
devices/{device_id}/error                # Error messages
devices/{device_id}/config/update        # Config updates
```

### 3. MQTT Bridge Service

**Location**: `fastapi_server/app/routers/mqtt_bridge.py`

**Responsibilities**:
- Subscribe to device command topics via GCP Pub/Sub
- Authenticate devices using JWT tokens or device certificates
- Route requests to existing backend services (STT, Agent, TTS)
- Publish responses back to device-specific topics
- Handle request queueing and rate limiting per device
- Store device configurations (language, voice, domain, etc.)

**Key Features**:
- **Stateless**: Each request contains device_id and session context
- **Async**: Non-blocking processing using asyncio
- **Modular**: Reuses existing services (no code duplication)
- **Scalable**: Can run multiple instances behind Cloud Run
- **Secure**: Device authentication + TLS encryption

### 4. Device Configuration Store

**Location**: Redis or Firestore

**Per-device config**:
```json
{
  "device_id": "rpi-toy-001",
  "user_id": "user-123",
  "tenant_id": "tenant-demo",
  "capabilities": ["stt", "tts", "chat"],
  "domain": "education",
  "language": "hi-IN",
  "tts_voice": "indic-hindi-female",
  "tts_provider": "qwen",
  "sample_rate_hz": 16000,
  "session_timeout_seconds": 3600,
  "custom_settings": {
    "button_actions": {
      "button_1": "help",
      "button_2": "repeat",
      "button_3": "next_topic"
    }
  }
}
```

## Message Flow Examples

### Flow 1: Full Voice Interaction (Toy A)

```
1. User speaks to toy
   RPi captures audio → publishes to devices/{id}/voice/query
   
2. MQTT Bridge receives message
   - Authenticates device
   - Loads device config
   - Extracts audio payload
   
3. Bridge calls existing services:
   a) STT service (Deepgram) → gets transcript
   b) Agent service → gets chat response (streaming)
   c) TTS service (Qwen) → synthesizes audio
   
4. Bridge publishes response
   - devices/{id}/voice/response (text + audio_b64)
   OR
   - devices/{id}/audio/chunk (streaming audio chunks)
   
5. RPi receives response
   - Plays audio through speaker
   - Shows text on screen (if available)
```

### Flow 2: TTS-Only Toy (Toy B)

```
1. External trigger (app/button) sends text
   RPi publishes to devices/{id}/synthesize
   Payload: {"text": "नमस्ते! आज का मौसम कैसा है?"}
   
2. Bridge processes
   - Loads device config (voice preference)
   - Calls TTS service directly
   
3. Bridge responds
   - devices/{id}/audio/chunk (audio_b64)
   
4. RPi plays audio
```

### Flow 3: STT-Only Toy (Toy C)

```
1. User speaks
   RPi publishes to devices/{id}/transcribe
   Payload: {audio_b64, sample_rate_hz}
   
2. Bridge processes
   - Calls STT service
   
3. Bridge responds
   - devices/{id}/transcript
   Payload: {text, confidence, language}
   
4. RPi forwards transcript to external system
```

### Flow 4: Custom Hardware Toy (Toy D)

```
1. User presses "Story Time" button
   RPi publishes to devices/{id}/text/query
   Payload: {text: "Tell me a story", session_id, context}
   
2. Bridge processes
   - Uses stored session context
   - Calls agent service with domain="education"
   - Gets streaming response
   
3. Bridge responds with audio
   - Multiple devices/{id}/audio/chunk messages
   
4. RPi plays story audio
   User presses "Stop" button → RPi cancels subscription
```

## Security Model

### Device Authentication

**Option 1: JWT Tokens (Recommended for MVP)**
- Device provisions with API key
- Exchanges API key for JWT token (24h expiry)
- JWT included in MQTT connection credentials
- Bridge validates JWT on each connection

**Option 2: Device Certificates (Production)**
- Each device has unique certificate
- Certificate-based mutual TLS (mTLS)
- Managed via GCP Certificate Manager
- Automatic rotation

### Authorization
- Device can only publish/subscribe to its own topics
- Topic pattern: `devices/{device_id}/*`
- GCP Pub/Sub enforces topic-level ACLs
- Bridge validates device_id matches authenticated identity

### Data Privacy
- All MQTT traffic encrypted via TLS
- Audio data is ephemeral (not logged)
- User data follows existing GDPR compliance
- Device config can be deleted via API

## Implementation Phases

### Phase 1: Core MQTT Bridge (Week 1)
- [ ] Set up GCP Pub/Sub topics
- [ ] Create MQTT bridge service
- [ ] Implement device authentication (JWT)
- [ ] Wire up existing STT/TTS/Agent services
- [ ] Basic error handling and logging

### Phase 2: RPi Client Library (Week 1-2)
- [ ] Python library for MQTT communication
- [ ] Audio capture (using PyAudio/sounddevice)
- [ ] Audio playback
- [ ] Configuration management
- [ ] Example scripts for different toy types

### Phase 3: Device Management (Week 2-3)
- [ ] Device registration API
- [ ] Config storage (Redis/Firestore)
- [ ] Web dashboard for device management
- [ ] OTA config updates via MQTT
- [ ] Session management and persistence

### Phase 4: Advanced Features (Week 3-4)
- [ ] Audio streaming (chunked responses)
- [ ] Multi-device synchronization
- [ ] Voice activity detection on device
- [ ] Wake word integration (optional)
- [ ] Offline mode with local fallback
- [ ] Analytics and usage tracking

### Phase 5: Production Hardening (Week 4+)
- [ ] Certificate-based auth
- [ ] Rate limiting per device
- [ ] Monitoring and alerting
- [ ] Load testing (100+ devices)
- [ ] Documentation and API reference
- [ ] Device SDK for other platforms (ESP32, Arduino)

## Cost Estimation

### GCP Services
- **Pub/Sub**: $40/month per 1TB (~ 10,000 devices x 100 msg/day)
- **Cloud Run (Bridge)**: $20-50/month (2 vCPU, 3GB, min-1 instance)
- **Firestore/Redis**: $10-30/month (device configs)
- **Total**: ~$70-120/month for 10,000 active devices

### Per-Device Traffic (High Usage)
- Voice queries: 50/day x 30KB = 1.5 MB/day
- Responses: 50/day x 50KB = 2.5 MB/day
- Total: ~4 MB/day/device = 120 MB/month
- Cost: $0.01-0.02/device/month

## Configuration Examples

### Toy Type A: Full Voice Assistant
```json
{
  "device_id": "rpi-edu-001",
  "capabilities": ["stt", "tts", "chat"],
  "domain": "education",
  "language": "hi-IN",
  "tts_voice": "indic-hindi-female",
  "tts_provider": "qwen",
  "enable_streaming": true,
  "session_timeout": 3600
}
```

### Toy Type B: Story Narrator (TTS-only)
```json
{
  "device_id": "rpi-story-002",
  "capabilities": ["tts"],
  "language": "ta-IN",
  "tts_voice": "indic-tamil-male",
  "tts_provider": "qwen",
  "enable_streaming": true
}
```

### Toy Type C: Voice Recorder (STT-only)
```json
{
  "device_id": "rpi-recorder-003",
  "capabilities": ["stt"],
  "language": "bn-IN",
  "sample_rate_hz": 16000,
  "confidence_threshold": 0.85
}
```

### Toy Type D: Smart Button Toy
```json
{
  "device_id": "rpi-button-004",
  "capabilities": ["chat", "tts"],
  "domain": "wellbeing",
  "language": "en-IN",
  "tts_voice": "indic-english-female",
  "button_mappings": {
    "red": "Tell me a joke",
    "blue": "What's the weather?",
    "green": "Help me relax"
  }
}
```

## Advantages of This Architecture

1. **Modular**: Each toy type uses only what it needs
2. **Scalable**: MQTT broker handles 100K+ devices
3. **Flexible**: Easy to add new capabilities/toy types
4. **Cost-effective**: Pay only for what you use
5. **Existing codebase**: Reuses all current services (STT, TTS, Agent)
6. **Secure**: Industry-standard MQTT security
7. **Offline capable**: Devices can queue messages during disconnection
8. **Real-time**: Low latency for voice interactions (<500ms STT+TTS)
9. **User-configurable**: Each device has personalized settings
10. **Multi-language**: Supports all 16 languages in current system

## Next Steps

1. **Review**: Get feedback on architecture
2. **Choose MQTT broker**: GCP Pub/Sub vs Cloud IoT Core vs self-hosted
3. **Start Phase 1**: Build MQTT bridge service
4. **Prototype**: Build reference RPi client for Toy Type A
5. **Test**: Validate latency and reliability
6. **Scale**: Load test with simulated devices
7. **Document**: API reference and integration guide
