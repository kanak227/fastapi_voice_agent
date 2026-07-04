# Using Domain Bots with MQTT Endpoints

Complete guide for using any domain bot with the MQTT IoT endpoints.

## Available Domain Bots

Your system has **10 domain bots**:

1. **religious** - Religious education
2. **education** - CBSE education (SmartE)
3. **digital-literacy** - AI and digital skills
4. **design-thinking** - Creative problem solving
5. **wellbeing** - Mental health and wellness
6. **sustainability** - Environmental topics
7. **global-citizenship** - Global awareness
8. **entrepreneurship** - Business skills
9. **emotional-intelligence** - EQ development
10. **financial-literacy** - Money management

## Configuration Methods

### Method 1: Set Domain During Device Registration (Recommended)

When you register a device, specify which domain bot it should use:

```python
from mqtt_voice_client import VoiceClient

client = VoiceClient(
    device_id="rpi-toy-001",
    api_url="https://your-backend.run.app",
    language="hi-IN",
)

# Register with EDUCATION domain
client.register_device(
    domain="education",  # ← Set domain here
    tts_voice="indic-hindi-female",
    tts_provider="qwen",
)
```

**Now all queries from this device will use the Education bot automatically!**

### Method 2: Change Domain for Existing Device

Update the domain for an already registered device:

```python
# Change to Wellbeing bot
client.update_config(domain="wellbeing")

# Change to Financial Literacy bot
client.update_config(domain="financial-literacy")

# Change to Sustainability bot
client.update_config(domain="sustainability")
```

### Method 3: Use Different Domains Per Session (Advanced)

If you want one device to access multiple domain bots, you need to specify the domain in each request using the REST API directly.

## Examples for Each Domain Bot

### 1. Education Bot (CBSE SmartE)

```python
client = VoiceClient(
    device_id="rpi-edu-001",
    api_url="https://your-backend.run.app",
    language="hi-IN",
)

client.register_device(
    domain="education",
    tts_voice="indic-hindi-female",
)

# Now use it
response = client.text_interaction("भारत की राजधानी क्या है?")
# Bot will answer from CBSE education knowledge base
```

**REST API**:
```bash
curl -X POST https://your-backend.run.app/mqtt/devices/rpi-edu-001/text/query \
  -H "Content-Type: application/json" \
  -d '{
    "text": "भारत की राजधानी क्या है?",
    "session_id": "session-123"
  }'
```

### 2. Wellbeing Bot (Mental Health)

```python
client.register_device(
    domain="wellbeing",
    tts_voice="indic-english-female",
)

response = client.text_interaction("I'm feeling stressed today")
# Bot provides mental health support and relaxation techniques
```

**REST API**:
```bash
curl -X POST https://your-backend.run.app/mqtt/devices/rpi-wellbeing-001/text/query \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I am feeling stressed today",
    "language": "en-IN"
  }'
```

### 3. Financial Literacy Bot

```python
client.register_device(
    domain="financial-literacy",
    tts_voice="indic-hindi-male",
)

response = client.text_interaction("बचत क्या है और मुझे क्यों करनी चाहिए?")
# Bot explains savings, investments, budgeting
```

**REST API**:
```bash
curl -X POST https://your-backend.run.app/mqtt/devices/rpi-finance-001/text/query \
  -H "Content-Type: application/json" \
  -d '{
    "text": "बचत क्या है और मुझे क्यों करनी चाहिए?",
    "language": "hi-IN"
  }'
```

### 4. Entrepreneurship Bot

```python
client.register_device(
    domain="entrepreneurship",
    tts_voice="indic-english-male",
)

response = client.text_interaction("How do I start a small business?")
# Bot provides business guidance and entrepreneurship tips
```

### 5. Sustainability Bot

```python
client.register_device(
    domain="sustainability",
    tts_voice="indic-tamil-female",
)

response = client.text_interaction("காலநிலை மாற்றம் என்றால் என்ன?")
# Bot explains environmental topics, climate change, sustainability
```

### 6. Emotional Intelligence Bot

```python
client.register_device(
    domain="emotional-intelligence",
    tts_voice="indic-hindi-female",
)

response = client.text_interaction("मैं अपनी भावनाओं को कैसे समझूं?")
# Bot helps with emotional awareness and social skills
```

### 7. Design Thinking Bot

```python
client.register_device(
    domain="design-thinking",
    tts_voice="indic-english-female",
)

response = client.text_interaction("What is design thinking?")
# Bot teaches creative problem-solving methodologies
```

### 8. Digital Literacy Bot

```python
client.register_device(
    domain="digital-literacy",
    tts_voice="indic-hindi-female",
)

response = client.text_interaction("इंटरनेट पर सुरक्षित कैसे रहें?")
# Bot teaches AI, digital skills, online safety
```

### 9. Global Citizenship Bot

```python
client.register_device(
    domain="global-citizenship",
    tts_voice="indic-english-female",
)

response = client.text_interaction("What is global citizenship?")
# Bot discusses global issues, cultural awareness, world topics
```

### 10. Religious Bot

```python
client.register_device(
    domain="religious",
    tts_voice="indic-hindi-male",
)

response = client.text_interaction("धर्म के मूल सिद्धांत क्या हैं?")
# Bot provides religious education and spiritual guidance
```

## Full REST API Examples

### Voice Query (STT + Bot + TTS)

```bash
# Record audio first, then:
AUDIO_B64=$(base64 -w 0 recording.wav)

curl -X POST https://your-backend.run.app/mqtt/devices/rpi-toy-001/voice/query \
  -H "Content-Type: application/json" \
  -d '{
    "audio_b64": "'$AUDIO_B64'",
    "sample_rate_hz": 16000,
    "session_id": "session-123",
    "language": "hi-IN"
  }'
```

**Response**:
```json
{
  "success": true,
  "device_id": "rpi-toy-001",
  "request_id": "uuid-123",
  "timestamp": "2026-06-13T10:30:00Z",
  "data": {
    "transcript": "भारत की राजधानी क्या है?",
    "response_text": "भारत की राजधानी नई दिल्ली है।",
    "audio_b64": "UklGRi4A...",
    "mime_type": "audio/wav",
    "voice": "indic-hindi-female"
  }
}
```

### Text Query (Bot + TTS)

```bash
curl -X POST https://your-backend.run.app/mqtt/devices/rpi-toy-001/text/query \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Tell me about photosynthesis",
    "session_id": "session-123",
    "language": "en-IN"
  }'
```

**Response**:
```json
{
  "success": true,
  "device_id": "rpi-toy-001",
  "request_id": "uuid-456",
  "data": {
    "response_text": "Photosynthesis is the process by which plants...",
    "audio_b64": "UklGRi4A...",
    "mime_type": "audio/wav",
    "voice": "indic-english-female"
  }
}
```

### TTS Only (No Bot)

```bash
curl -X POST https://your-backend.run.app/mqtt/devices/rpi-toy-001/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "नमस्ते! मैं SmartE हूँ।",
    "language": "hi-IN",
    "voice": "indic-hindi-female",
    "format": "wav"
  }'
```

**Response**:
```json
{
  "success": true,
  "device_id": "rpi-toy-001",
  "request_id": "uuid-789",
  "data": {
    "audio_b64": "UklGRi4A...",
    "mime_type": "audio/wav",
    "voice": "indic-hindi-female"
  }
}
```

### STT Only (No Bot)

```bash
AUDIO_B64=$(base64 -w 0 recording.wav)

curl -X POST https://your-backend.run.app/mqtt/devices/rpi-toy-001/transcribe \
  -H "Content-Type: application/json" \
  -d '{
    "audio_b64": "'$AUDIO_B64'",
    "sample_rate_hz": 16000,
    "language": "hi-IN"
  }'
```

**Response**:
```json
{
  "success": true,
  "device_id": "rpi-toy-001",
  "request_id": "uuid-101",
  "data": {
    "transcript": "भारत की राजधानी क्या है?",
    "confidence": 0.95,
    "language": "hi"
  }
}
```

## Device Configuration Management

### View Current Configuration

```bash
curl https://your-backend.run.app/mqtt/devices/rpi-toy-001/config
```

**Response**:
```json
{
  "device_id": "rpi-toy-001",
  "tenant_id": "tenant-demo",
  "domain": "education",  ← Current domain
  "language": "hi-IN",
  "tts_voice": "indic-hindi-female",
  "tts_provider": "qwen",
  "capabilities": {
    "stt": true,
    "tts": true,
    "chat": true,
    "streaming": false
  }
}
```

### Update Domain

```bash
# Get current config first
CONFIG=$(curl -s https://your-backend.run.app/mqtt/devices/rpi-toy-001/config)

# Modify domain field
NEW_CONFIG=$(echo $CONFIG | jq '.domain = "wellbeing"')

# Update
curl -X PUT https://your-backend.run.app/mqtt/devices/rpi-toy-001/config \
  -H "Content-Type: application/json" \
  -d "$NEW_CONFIG"
```

**Or with Python**:
```python
client.update_config(domain="wellbeing")
```

### Register Multiple Devices with Different Domains

```python
# Education toy
education_client = VoiceClient(
    device_id="rpi-edu-001",
    api_url=API_URL,
    language="hi-IN",
)
education_client.register_device(domain="education", tts_voice="indic-hindi-female")

# Wellbeing toy
wellbeing_client = VoiceClient(
    device_id="rpi-wellbeing-001",
    api_url=API_URL,
    language="en-IN",
)
wellbeing_client.register_device(domain="wellbeing", tts_voice="indic-english-female")

# Finance toy
finance_client = VoiceClient(
    device_id="rpi-finance-001",
    api_url=API_URL,
    language="hi-IN",
)
finance_client.register_device(domain="financial-literacy", tts_voice="indic-hindi-male")
```

## Multi-Domain Toy (Advanced)

If you want ONE device to access MULTIPLE domain bots, you need to work directly with the backend agent API instead of MQTT endpoints. Here's how:

### Option 1: Change Domain Config Before Each Query

```python
# Start with education
client.update_config(domain="education")
response = client.text_interaction("भारत की राजधानी क्या है?")

# Switch to wellbeing
client.update_config(domain="wellbeing")
response = client.text_interaction("I feel stressed")

# Switch to finance
client.update_config(domain="financial-literacy")
response = client.text_interaction("बचत के बारे में बताओ")
```

### Option 2: Use Agent API Directly (Bypass MQTT)

```python
import requests

# Direct agent API call with domain override
response = requests.post(
    f"{API_URL}/agent/stream",
    headers={"X-Tenant-Id": "tenant-demo"},
    json={
        "session_id": "session-123",
        "input_type": "text",
        "text": "भारत की राजधानी क्या है?",
        "domain": "education",  # Override domain per request
        "language": "hi-IN",
        "output_audio": True,
        "tts_provider": "qwen",
        "tts_voice": "indic-hindi-female",
    },
    stream=True,
)
```

## Complete Working Examples

### Example 1: Education Toy (Hindi)

```python
#!/usr/bin/env python3
from mqtt_voice_client import VoiceClient

# Configure
client = VoiceClient(
    device_id="rpi-edu-hindi-001",
    api_url="https://your-backend.run.app",
    language="hi-IN",
)

# Register with EDUCATION domain
client.register_device(
    domain="education",
    tts_voice="indic-hindi-female",
    tts_provider="qwen",
)

# Use it!
while True:
    input("Press Enter to ask a question...")
    
    # Record voice query
    audio = client.record_audio(duration=5.0)
    
    # Send to EDUCATION bot
    response = client.send_voice_query_sync(audio)
    
    if response["success"]:
        print(f"You said: {response['data']['transcript']}")
        print(f"SmartE replied: {response['data']['response_text']}")
        
        # Play audio response
        import base64
        audio_bytes = base64.b64decode(response['data']['audio_b64'])
        client.play_audio(audio_bytes)
    else:
        print(f"Error: {response['error']}")
```

### Example 2: Wellbeing Toy (English)

```python
#!/usr/bin/env python3
from mqtt_voice_client import VoiceClient

client = VoiceClient(
    device_id="rpi-wellbeing-001",
    api_url="https://your-backend.run.app",
    language="en-IN",
)

# Register with WELLBEING domain
client.register_device(
    domain="wellbeing",
    tts_voice="indic-english-female",
)

# Mental health support
queries = [
    "I'm feeling stressed",
    "How can I relax?",
    "Tell me a breathing exercise",
]

for query in queries:
    print(f"\nQuery: {query}")
    response = client.text_interaction(query, play_response=True)
    if response["success"]:
        print(f"Response: {response['data']['response_text']}\n")
```

### Example 3: Multi-Topic Button Toy

```python
#!/usr/bin/env python3
from mqtt_voice_client import VoiceClient
import RPi.GPIO as GPIO

# Setup GPIO buttons
BUTTON_EDUCATION = 17
BUTTON_WELLBEING = 27
BUTTON_FINANCE = 22

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_EDUCATION, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_WELLBEING, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_FINANCE, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Initialize client
client = VoiceClient(
    device_id="rpi-multi-001",
    api_url="https://your-backend.run.app",
    language="hi-IN",
)

# Default to education
client.register_device(domain="education", tts_voice="indic-hindi-female")

try:
    while True:
        if GPIO.input(BUTTON_EDUCATION) == GPIO.LOW:
            print("Education button pressed")
            client.update_config(domain="education")
            response = client.text_interaction("विज्ञान क्या है?")
            
        elif GPIO.input(BUTTON_WELLBEING) == GPIO.LOW:
            print("Wellbeing button pressed")
            client.update_config(domain="wellbeing")
            response = client.text_interaction("मुझे आराम करने में मदद करो")
            
        elif GPIO.input(BUTTON_FINANCE) == GPIO.LOW:
            print("Finance button pressed")
            client.update_config(domain="financial-literacy")
            response = client.text_interaction("बचत के बारे में बताओ")
        
        time.sleep(0.1)
        
except KeyboardInterrupt:
    GPIO.cleanup()
```

## Domain-Specific Features

### Education Bot
- CBSE curriculum aligned
- Subjects: Math, Science, Social Studies, Languages
- Grade-specific content
- Study tips and exam prep

### Wellbeing Bot
- Mental health support
- Stress management
- Mindfulness exercises
- Emotional support

### Financial Literacy Bot
- Savings and budgeting
- Investment basics
- Banking concepts
- Financial planning

### Entrepreneurship Bot
- Business fundamentals
- Startup guidance
- Marketing and sales
- Leadership skills

### Sustainability Bot
- Climate change
- Environmental protection
- Sustainable living
- Conservation topics

### Emotional Intelligence Bot
- Self-awareness
- Empathy development
- Social skills
- Emotional regulation

### Design Thinking Bot
- Creative problem solving
- Innovation methodologies
- Prototyping and testing
- User-centered design

### Digital Literacy Bot
- AI and technology
- Online safety
- Digital skills
- Coding basics

### Global Citizenship Bot
- World cultures
- Global issues
- International awareness
- Human rights

### Religious Bot
- Religious education
- Spiritual guidance
- Moral values
- Faith traditions

## Testing All Domains

```python
#!/usr/bin/env python3
"""Test all domain bots"""
from mqtt_voice_client import VoiceClient

API_URL = "https://your-backend.run.app"
LANGUAGE = "en-IN"

domains = [
    ("education", "What is photosynthesis?"),
    ("wellbeing", "I feel stressed"),
    ("financial-literacy", "What is savings?"),
    ("entrepreneurship", "How to start a business?"),
    ("sustainability", "What is climate change?"),
    ("emotional-intelligence", "How to be more empathetic?"),
    ("design-thinking", "What is design thinking?"),
    ("digital-literacy", "What is AI?"),
    ("global-citizenship", "What is global citizenship?"),
    ("religious", "What are core values?"),
]

client = VoiceClient(
    device_id="test-all-domains",
    api_url=API_URL,
    language=LANGUAGE,
)

for domain, query in domains:
    print(f"\n{'='*60}")
    print(f"Testing: {domain.upper()}")
    print(f"Query: {query}")
    print('='*60)
    
    # Update to this domain
    client.update_config(domain=domain)
    
    # Query
    response = client.send_text_query_sync(query)
    
    if response["success"]:
        print(f"✅ Success")
        print(f"Response: {response['data']['response_text'][:200]}...")
    else:
        print(f"❌ Failed: {response['error']}")
```

## Summary

**To use any domain bot**:

1. **Set domain during registration**: `client.register_device(domain="education")`
2. **Or update domain later**: `client.update_config(domain="wellbeing")`
3. **Then use normally**: All queries go to that domain bot automatically

The domain is stored in the device config on the backend, so you only set it once and all subsequent requests use that bot!
