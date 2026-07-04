# Web API Integration Guide

## Base URL
```
https://multi-bot-server-t5wdyzp3ta-uc.a.run.app
```

## Table of Contents
1. [Authentication](#authentication)
2. [Core Endpoints](#core-endpoints)
3. [Request/Response Formats](#requestresponse-formats)
4. [Error Handling](#error-handling)
5. [Environment Setup](#environment-setup)
6. [Code Examples](#code-examples)

---

## Authentication

### Required Headers
All requests must include:
```http
X-Tenant-Id: your-tenant-id
Content-Type: application/json
```

**Tenant ID Rules:**
- Max 64 characters
- Alphanumeric, dots, underscores, hyphens only: `[A-Za-z0-9._-]+`
- Example: `web-client-123`, `mobile-app-v1`

---

## Core Endpoints

### 1. Health Check
**GET** `/health`

Check if the server is running.

**Response:**
```json
{
  "status": "ok"
}
```

---

### 2. List Available Domains
**GET** `/agent/domains`

Get all available bot domains (subjects/topics).

**Response:**
```json
{
  "domains": [
    "religious",
    "education",
    "digital-literacy",
    "design-thinking",
    "wellbeing",
    "sustainability",
    "global-citizenship",
    "entrepreneurship",
    "emotional-intelligence",
    "financial-literacy"
  ],
  "count": 10
}
```

---

### 3. Chat Stream (Text + Audio)
**POST** `/agent/stream`

Send a text or audio message and get a streaming response with optional voice output.

**Request Body:**
```json
{
  "session_id": "unique-session-id",
  "input_type": "text",
  "text": "Hello, tell me about Indian mythology",
  "domain": "religious",
  "language": "en-US",
  "use_knowledge": true,
  "knowledge_top_k": 3,
  "output_audio": true,
  "tts_provider": "elevenlabs",
  "tts_voice": "hpp4J3VqNfWAUOO0d1Us",
  "tts_format": "mp3_44100_128",
  "provider": "gemini",
  "llm_model": "gemini-2.0-flash"
}
```

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Unique identifier for conversation continuity |
| `input_type` | string | Yes | `"text"` or `"audio"` |
| `text` | string | Conditional | Required if `input_type="text"` |
| `audio` | object | Conditional | Required if `input_type="audio"` (see Audio Input below) |
| `domain` | string | Yes | One of the domains from `/agent/domains` |
| `language` | string | No | Default: `"en-US"`. Supports: `en-US`, `hi-IN`, `ta-IN`, `te-IN`, `mr-IN`, `bn-IN`, `gu-IN`, `kn-IN`, `ml-IN`, `pa-IN`, `fr-FR`, `de-DE`, `es-ES`, `ar-SA`, `zh-CN`, `ja-JP` |
| `use_knowledge` | boolean | No | Default: `true`. Enable knowledge base retrieval |
| `knowledge_top_k` | number | No | Default: 3. Number of knowledge chunks to retrieve |
| `output_audio` | boolean | No | Default: `false`. Generate voice response |
| `tts_provider` | string | No | `"elevenlabs"` (cloud, high quality) or `"qwen"` (offline, requires GPU VM) |
| `tts_voice` | string | No | Voice ID (see `/voice/voices` endpoint) |
| `tts_format` | string | No | Audio format: `"mp3_44100_128"`, `"pcm_24000"`, etc. |
| `tts_emotion` | string | No | Emotion for voice: `"neutral"`, `"happy"`, `"sad"`, etc. |
| `provider` | string | No | LLM provider: `"gemini"`, `"openai"`, `"anthropic"` |
| `llm_model` | string | No | Model name: `"gemini-2.0-flash"`, `"gpt-4o"`, etc. |
| `history` | array | No | Conversation history (array of `{role, content}` objects) |

**Audio Input Object:**
```json
{
  "audio": {
    "audio_b64": "base64-encoded-audio-data",
    "sample_rate_hz": 16000,
    "transport": "http"
  }
}
```

**Response Format:**
Server-Sent Events (SSE) stream with multiple event types:

**Event: `input`**
```
event: input
data: {"transcript": "recognized text", "confidence": 0.95, "language": "en-US"}
```

**Event: `text`**
```
event: text
data: "Hello! "
```

**Event: `audio`** (if `output_audio=true`)
```
event: audio
data: {
  "index": 0,
  "text": "Hello!",
  "mime_type": "audio/mpeg",
  "audio_b64": "base64-encoded-audio"
}
```

**Event: `final_text`**
```
event: final_text
data: "Hello! Indian mythology is fascinating..."
```

**Event: `done`**
```
event: done
data: {"ok": true, "request_id": "uuid"}
```

---

### 4. WebSocket Chat
**WebSocket** `/agent/ws`

Real-time bidirectional voice/text chat.

**Connection:**
```javascript
const ws = new WebSocket(
  'wss://multi-bot-server-t5wdyzp3ta-uc.a.run.app/agent/ws',
  {
    headers: {
      'x-tenant-id': 'your-tenant-id'
    }
  }
);
```

**Message Types:**

**1. Start Session:**
```json
{
  "type": "start",
  "session_id": "unique-session-id",
  "sample_rate_hz": 16000,
  "language": "en-US",
  "domain": "religious",
  "output_audio": true,
  "tts_voice": "hpp4J3VqNfWAUOO0d1Us",
  "tts_provider": "elevenlabs"
}
```

**2. Send Audio Chunk:**
```json
{
  "type": "audio_chunk",
  "audio_b64": "base64-encoded-pcm16-audio"
}
```

**3. End Audio / Process Turn:**
```json
{
  "type": "end_audio"
}
```

**Server Events:**
```json
{"event": "ready", "data": {"session_id": "..."}}
{"event": "started", "data": {"session_id": "..."}}
{"event": "buffering", "data": {"buffered_ms": 1500}}
{"event": "processing", "data": {}}
{"event": "input", "data": {"transcript": "...", "confidence": 0.95}}
{"event": "text", "data": "response text"}
{"event": "audio", "data": {"index": 0, "audio_b64": "...", "mime_type": "audio/mpeg"}}
{"event": "done", "data": {"ok": true}}
```

---

### 5. Voice Transcription (STT)
**POST** `/voice/transcribe`

Convert audio to text.

**Request:**
```json
{
  "audio": {
    "audio_b64": "base64-encoded-audio",
    "sample_rate_hz": 16000
  },
  "language": "en-US",
  "request_id": "optional-request-id"
}
```

**Response:**
```json
{
  "text": "transcribed text",
  "confidence": 0.95,
  "language": "en-US",
  "request_id": "uuid"
}
```

---

### 6. Text-to-Speech
**POST** `/voice/synthesize`

Convert text to audio.

**Request:**
```json
{
  "text": "Hello, how are you?",
  "language": "en-US",
  "voice": "hpp4J3VqNfWAUOO0d1Us",
  "tts_provider": "elevenlabs",
  "output_format": "mp3_44100_128",
  "emotion": "neutral",
  "request_id": "optional-request-id"
}
```

**Response:**
```json
{
  "request_id": "uuid",
  "provider": "DeepgramElevenLabsProvider",
  "voice": "hpp4J3VqNfWAUOO0d1Us",
  "mime_type": "audio/mpeg",
  "audio_b64": "base64-encoded-audio-data"
}
```

---

### 7. List Available Voices
**GET** `/voice/voices`

**Query Parameters:**
- `tts_provider` (optional): `"elevenlabs"` or `"qwen"`
- `language` (optional): Filter by language (e.g., `"en"`, `"hi"`, `"ta"`)

**Response:**
```json
[
  {
    "name": "Rachel",
    "voice_id": "hpp4J3VqNfWAUOO0d1Us",
    "language": "en-US",
    "description": "American Female"
  },
  {
    "name": "Serena",
    "voice_id": "serena",
    "language": "en-US",
    "description": "American Female (Offline)"
  }
]
```

---

### 8. Voice Health Check
**GET** `/voice/health`

Check if voice services are available.

**Response:**
```json
{
  "status": "ok"
}
```

Possible statuses: `"ok"`, `"unhealthy"`, `"disabled"`

---

### 9. MQTT Bridge (IoT Devices)
**POST** `/mqtt/send`

Send a message to an MQTT-connected device.

**Request:**
```json
{
  "device_id": "toy-001",
  "message": "Hello from the server!",
  "audio_b64": "optional-base64-audio",
  "metadata": {
    "language": "en-US",
    "voice": "Rachel"
  }
}
```

**Response:**
```json
{
  "ok": true,
  "message_id": "uuid"
}
```

---

## Error Handling

### HTTP Status Codes
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (missing/invalid tenant ID)
- `404` - Not Found (invalid domain)
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error
- `502` - Bad Gateway (upstream service unavailable)

### Error Response Format
```json
{
  "detail": "error message",
  "error": "error_code",
  "status_code": 400
}
```

### Common Errors
- `missing_tenant_id` - X-Tenant-Id header not provided
- `invalid_tenant_id` - Tenant ID format is invalid
- `domain_not_resolved` - Invalid domain specified
- `input_normalization_failed` - Unable to process input
- `bot_http` - Domain bot returned an error
- `bot_transport` - Cannot connect to domain bot
- `tts_failed` - Voice synthesis failed
- `stt_failed` - Speech recognition failed

---

## Environment Setup

### Required Secrets/Configuration

#### 1. API Keys (Contact Admin for Production Keys)

**LLM Provider (Gemini):**
```bash
GEMINI_API_KEY=AIzaSyA6JS52xs_7ZQKtZkaUa1IqKDzfC-ikz50
GEMINI_MODEL=gemini-2.0-flash
```

**Speech Services (Deepgram + ElevenLabs):**
```bash
DEEPGRAM_API_KEY=756d8e102485a4c1e1b2fd2a5e0d5d14cd8d0363
ELEVENLABS_API_KEY=sk_dfb686c3543dde54c6b79ca948fc6a0382ac5f1f34171c13
```

**Vector Database (Qdrant):**
```bash
QDRANT_URL=https://777c2b93-cccc-45ac-aa8a-4e635d933291.eu-west-2-0.aws.cloud.qdrant.io
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6NTVlMThiM2UtMmJjMC00ZGZkLWIxYmEtZTUxYjA2MDcxNzgwIn0.5zfPN-0tyKFzrfaFRkXpWmlWb7_gK-_xG1oyjAazrP4
```

**Embeddings (Gemini):**
```bash
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=gemini-embedding-001
GEMINI_API_KEY=AIzaSyCfF2p0Cs_KR38ZbT9NzkFiGRfaLs0wtoI
```

**Cache (Redis):**
```bash
REDIS_URL=rediss://default:NCKU4ilH8fT65ALZbm2yGe7T9djhkXb0@redis-12523.c326.us-east-1-3.ec2.cloud.redislabs.com:12523/0
```

#### 2. Optional Configuration

**Offline TTS (Qwen3 - requires GPU VM):**
```bash
QWEN_TTS_BASE_URL=http://your-vm-ip:8000/v1
QWEN_TTS_API_KEY=optional-api-key
```

**CORS Settings:**
```bash
CORS_ALLOW_ORIGINS=https://your-frontend.com,https://another-domain.com
CORS_ALLOW_CREDENTIALS=true
```

---

## Code Examples

### JavaScript/TypeScript (Fetch API)

#### Simple Text Chat
```javascript
const BASE_URL = 'https://multi-bot-server-t5wdyzp3ta-uc.a.run.app';

async function sendMessage(message, domain = 'religious') {
  const response = await fetch(`${BASE_URL}/agent/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-Id': 'web-client-001'
    },
    body: JSON.stringify({
      session_id: 'session-' + Date.now(),
      input_type: 'text',
      text: message,
      domain: domain,
      language: 'en-US',
      output_audio: false
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let fullResponse = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        try {
          const parsed = JSON.parse(data);
          if (typeof parsed === 'string') {
            fullResponse += parsed;
            console.log('Text:', parsed);
          }
        } catch (e) {
          // Not JSON, might be plain text
        }
      } else if (line.startsWith('event: ')) {
        const event = line.slice(7);
        console.log('Event:', event);
      }
    }
  }

  return fullResponse;
}

// Usage
sendMessage('Tell me about Lord Rama', 'religious')
  .then(response => console.log('Complete:', response));
```

#### Chat with Voice Output
```javascript
async function sendMessageWithVoice(message, domain = 'religious') {
  const response = await fetch(`${BASE_URL}/agent/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-Id': 'web-client-001'
    },
    body: JSON.stringify({
      session_id: 'session-' + Date.now(),
      input_type: 'text',
      text: message,
      domain: domain,
      language: 'en-US',
      output_audio: true,
      tts_provider: 'elevenlabs',
      tts_voice: 'hpp4J3VqNfWAUOO0d1Us',
      tts_format: 'mp3_44100_128'
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const audioChunks = [];

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('event: audio')) {
        // Next line has the data
        continue;
      }
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        try {
          const parsed = JSON.parse(data);
          if (parsed.audio_b64) {
            // Convert base64 to audio and play
            const audioBlob = base64ToBlob(parsed.audio_b64, parsed.mime_type);
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);
            audio.play();
          }
        } catch (e) {}
      }
    }
  }
}

function base64ToBlob(base64, mimeType) {
  const byteCharacters = atob(base64);
  const byteArrays = [];

  for (let i = 0; i < byteCharacters.length; i++) {
    byteArrays.push(byteCharacters.charCodeAt(i));
  }

  return new Blob([new Uint8Array(byteArrays)], { type: mimeType });
}
```

#### WebSocket Example
```javascript
class VoiceChat {
  constructor(tenantId) {
    this.tenantId = tenantId;
    this.ws = null;
    this.sessionId = 'session-' + Date.now();
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(
        `wss://multi-bot-server-t5wdyzp3ta-uc.a.run.app/agent/ws?tenant_id=${this.tenantId}`
      );

      this.ws.onopen = () => {
        console.log('WebSocket connected');
      };

      this.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        console.log('Event:', msg.event, 'Data:', msg.data);

        if (msg.event === 'ready') {
          resolve(msg.data.session_id);
        } else if (msg.event === 'audio') {
          this.playAudio(msg.data.audio_b64, msg.data.mime_type);
        } else if (msg.event === 'text') {
          console.log('Bot says:', msg.data);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };
    });
  }

  startSession(domain = 'religious', language = 'en-US') {
    this.ws.send(JSON.stringify({
      type: 'start',
      session_id: this.sessionId,
      sample_rate_hz: 16000,
      language: language,
      domain: domain,
      output_audio: true,
      tts_provider: 'elevenlabs',
      tts_voice: 'hpp4J3VqNfWAUOO0d1Us'
    }));
  }

  sendAudioChunk(audioBase64) {
    this.ws.send(JSON.stringify({
      type: 'audio_chunk',
      audio_b64: audioBase64
    }));
  }

  endAudio() {
    this.ws.send(JSON.stringify({
      type: 'end_audio'
    }));
  }

  playAudio(base64Audio, mimeType) {
    const audioBlob = base64ToBlob(base64Audio, mimeType);
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);
    audio.play();
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Usage
const chat = new VoiceChat('web-client-001');
chat.connect().then(sessionId => {
  console.log('Connected with session:', sessionId);
  chat.startSession('religious', 'en-US');
  // ... send audio chunks from microphone ...
});
```

### Python Example
```python
import requests
import json
import base64

BASE_URL = 'https://multi-bot-server-t5wdyzp3ta-uc.a.run.app'
TENANT_ID = 'python-client-001'

def send_message(message, domain='religious'):
    url = f'{BASE_URL}/agent/stream'
    headers = {
        'Content-Type': 'application/json',
        'X-Tenant-Id': TENANT_ID
    }
    payload = {
        'session_id': f'session-{int(time.time())}',
        'input_type': 'text',
        'text': message,
        'domain': domain,
        'language': 'en-US',
        'output_audio': False
    }

    response = requests.post(url, headers=headers, json=payload, stream=True)
    
    full_response = ''
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = line[6:]
                try:
                    parsed = json.loads(data)
                    if isinstance(parsed, str):
                        full_response += parsed
                        print(f'Text: {parsed}')
                except json.JSONDecodeError:
                    pass
    
    return full_response

# Usage
response = send_message('Tell me about Indian mythology', 'religious')
print(f'Complete response: {response}')
```

---

## Rate Limiting

The API implements rate limiting to prevent abuse:
- 100 requests per minute per tenant ID
- 1000 requests per hour per tenant ID

If you exceed limits, you'll receive a `429 Too Many Requests` response.

---

## Best Practices

1. **Session Management**: Use unique session IDs for each conversation
2. **Error Handling**: Always handle network errors and retry with exponential backoff
3. **Audio Streaming**: For real-time voice, use WebSocket instead of HTTP
4. **Chunking**: When sending audio, send in ~500ms chunks for better responsiveness
5. **Language Detection**: The system can auto-detect language from audio input
6. **Voice Selection**: Use `/voice/voices` to get appropriate voices for each language
7. **Knowledge Base**: Enable `use_knowledge=true` for fact-based responses
8. **Caching**: The system caches embeddings and retrieval results - repeated queries are faster

---

## Support & Resources

- **API Status**: Monitor at `/health` and `/voice/health`
- **Available Domains**: Check `/agent/domains` for current bot list
- **Voice Options**: Query `/voice/voices` for supported voices
- **Documentation**: See `/docs` for interactive API documentation (Swagger UI)

---

## Additional Notes

### Supported Languages
- **English**: `en-US`, `en-GB`
- **Hindi**: `hi-IN`
- **Tamil**: `ta-IN`
- **Telugu**: `te-IN`
- **Marathi**: `mr-IN`
- **Bengali**: `bn-IN`
- **Gujarati**: `gu-IN`
- **Kannada**: `kn-IN`
- **Malayalam**: `ml-IN`
- **Punjabi**: `pa-IN`
- **French**: `fr-FR`
- **German**: `de-DE`
- **Spanish**: `es-ES`
- **Arabic**: `ar-SA`
- **Chinese**: `zh-CN`
- **Japanese**: `ja-JP`

### Audio Formats
- **Input**: PCM16 (16-bit PCM, mono, any sample rate)
- **Output**: MP3, PCM, WAV, OGG, WebM

### TTS Providers
- **ElevenLabs**: High-quality cloud TTS (requires API key)
- **Qwen**: Offline multilingual TTS (requires GPU VM deployment)

---

**Last Updated**: 2026-07-04
**API Version**: 1.0
