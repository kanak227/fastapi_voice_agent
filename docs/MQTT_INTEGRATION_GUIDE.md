# MQTT IoT Integration Guide

Complete guide for integrating Raspberry Pi voice toys with the GCP-based chatbot service.

## Table of Contents

1. [Overview](#overview)
2. [Backend Setup](#backend-setup)
3. [Raspberry Pi Setup](#raspberry-pi-setup)
4. [Device Registration](#device-registration)
5. [Testing](#testing)
6. [Production Deployment](#production-deployment)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The MQTT IoT system connects Raspberry Pi devices to your existing FastAPI backend through HTTP endpoints. In production, these endpoints can be triggered via GCP Pub/Sub for true MQTT integration.

### System Architecture

```
RPi Device → HTTP/MQTT → Backend → (STT + Agent + TTS) → Response → Device
```

### Key Components

1. **Backend**: FastAPI MQTT bridge service (`/mqtt/*` endpoints)
2. **Client Library**: Python library for RPi (`mqtt_voice_client`)
3. **Device Config**: Per-device settings stored in backend
4. **Examples**: Reference implementations for different toy types

---

## Backend Setup

### 1. Deploy Updated Backend

The MQTT bridge router is already integrated into your FastAPI backend.

**Changes made**:
- Added `/mqtt/` router in `app/routers/mqtt_bridge.py`
- Registered router in `app/main.py`
- Supports all device types (STT, TTS, Chat)

**Deploy to GCP**:

```bash
cd deployment/gcp
gcloud builds submit --config=cloudbuild.yaml
```

This will deploy the updated backend with MQTT endpoints.

### 2. Verify Deployment

Check that the new endpoints are live:

```bash
# Get your backend URL
BACKEND_URL=$(gcloud run services describe multi-bot-server --region=us-central1 --format='value(status.url)')

# Test health endpoint
curl $BACKEND_URL/health

# Test MQTT endpoints exist
curl $BACKEND_URL/docs | grep mqtt
```

You should see:
- `/mqtt/devices/register`
- `/mqtt/devices/{device_id}/voice/query`
- `/mqtt/devices/{device_id}/text/query`
- `/mqtt/devices/{device_id}/transcribe`
- `/mqtt/devices/{device_id}/synthesize`

### 3. Configure CORS (if testing from web app)

If you're testing from a web interface, ensure CORS allows your origin:

```bash
# In .env or Cloud Run environment variables
CORS_ALLOW_ORIGINS=*
# OR
CORS_ALLOW_ORIGINS=https://your-frontend.app,http://localhost:3000
```

---

## Raspberry Pi Setup

### 1. Install Raspberry Pi OS

Use Raspberry Pi Imager to install:
- **Recommended**: Raspberry Pi OS Lite (64-bit) for headless operation
- **Alternative**: Raspberry Pi OS with Desktop for development

**Enable SSH** during setup for remote access.

### 2. Update System

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### 3. Install Python Dependencies

```bash
# Install Python 3.9+
sudo apt-get install -y python3 python3-pip python3-dev

# Install audio libraries
sudo apt-get install -y portaudio19-dev libasound2-dev

# Install GPIO library (for button-based toys)
sudo apt-get install -y python3-rpi.gpio
```

### 4. Install MQTT Voice Client

```bash
# Clone repository (or copy files via SCP)
git clone https://github.com/your-org/your-repo.git
cd your-repo/raspberry_pi/mqtt_voice_client

# Install dependencies
pip3 install -r requirements.txt
```

### 5. Test Audio

**Test microphone**:
```bash
arecord -d 5 -f cd test.wav
aplay test.wav
```

**Test speaker**:
```bash
speaker-test -t wav -c 2
```

**Adjust volumes**:
```bash
alsamixer
# Use arrow keys to adjust, Esc to exit
```

---

## Device Registration

### Method 1: Programmatic Registration (Recommended)

```python
from mqtt_voice_client import VoiceClient

client = VoiceClient(
    device_id="rpi-edu-001",
    api_url="https://your-backend.run.app",
    language="hi-IN",
)

# Register device
client.register_device(
    domain="education",
    tts_voice="indic-hindi-female",
    tts_provider="qwen",
    capabilities={
        "stt": True,
        "tts": True,
        "chat": True,
        "streaming": False,
    },
)

print("Device registered!")
```

### Method 2: API Registration (for bulk setup)

```bash
curl -X POST https://your-backend.run.app/mqtt/devices/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "rpi-edu-001",
    "tenant_id": "tenant-demo",
    "capabilities": {
      "stt": true,
      "tts": true,
      "chat": true,
      "streaming": false
    },
    "domain": "education",
    "language": "hi-IN",
    "tts_voice": "indic-hindi-female",
    "tts_provider": "qwen",
    "sample_rate_hz": 16000
  }'
```

### View Device Configuration

```bash
curl https://your-backend.run.app/mqtt/devices/rpi-edu-001/config
```

### Update Configuration

```bash
curl -X PUT https://your-backend.run.app/mqtt/devices/rpi-edu-001/config \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "rpi-edu-001",
    "language": "ta-IN",
    "tts_voice": "indic-tamil-female"
  }'
```

---

## Testing

### Test 1: Full Voice Query (STT + Chat + TTS)

```python
from mqtt_voice_client import VoiceClient

client = VoiceClient(
    device_id="test-device-001",
    api_url="https://your-backend.run.app",
    language="hi-IN",
)

# Record and process
response = client.voice_interaction(
    duration=5.0,
    play_response=True,
)

print(f"Transcript: {response['data']['transcript']}")
print(f"Response: {response['data']['response_text']}")
```

### Test 2: Text Query (Chat + TTS)

```python
response = client.text_interaction(
    text="भारत की राजधानी क्या है?",
    play_response=True,
)

print(f"Response: {response['data']['response_text']}")
```

### Test 3: TTS Only

```python
response = client.synthesize_speech_sync(
    text="नमस्ते! मैं SmartE हूँ।"
)

import base64
audio = base64.b64decode(response['data']['audio_b64'])
client.play_audio(audio)
```

### Test 4: STT Only

```python
audio = client.record_audio(duration=5.0)
response = client.transcribe_audio_sync(audio)

print(f"Transcript: {response['data']['transcript']}")
print(f"Confidence: {response['data']['confidence']}")
```

---

## Production Deployment

### 1. Auto-Start Service

Create systemd service for your toy:

```bash
sudo nano /etc/systemd/system/voice-toy.service
```

```ini
[Unit]
Description=Voice Toy Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/mqtt_voice_client
ExecStart=/usr/bin/python3 /home/pi/mqtt_voice_client/examples/full_voice_toy.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable voice-toy.service
sudo systemctl start voice-toy.service
sudo systemctl status voice-toy.service
```

View logs:

```bash
sudo journalctl -u voice-toy.service -f
```

### 2. Watchdog for Network Recovery

Install watchdog:

```bash
sudo apt-get install -y watchdog
sudo systemctl enable watchdog
```

Configure in your Python script:

```python
import socket
import time

def check_network():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

while True:
    if not check_network():
        print("Network down, waiting...")
        time.sleep(10)
        continue
    
    # Your main loop here
    try:
        response = client.voice_interaction()
        # ...
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)
```

### 3. OTA Updates

Use Git for remote updates:

```bash
# On RPi
cd ~/mqtt_voice_client
git pull origin main
sudo systemctl restart voice-toy.service
```

Or use Ansible/Balena for fleet management.

### 4. Monitoring

**Check device status remotely**:

```bash
curl https://your-backend.run.app/mqtt/devices
```

**Log device interactions** (add to your script):

```python
import logging
logging.basicConfig(
    filename='/var/log/voice-toy.log',
    level=logging.INFO,
    format='%(asctime)s %(message)s'
)

logger.info(f"Query: {transcript}")
logger.info(f"Response: {response_text}")
```

---

## Troubleshooting

### Device registration fails with 404

**Cause**: Backend not deployed or URL incorrect.

**Fix**:
```bash
# Verify backend is running
curl https://your-backend.run.app/health

# Check if MQTT router is loaded
curl https://your-backend.run.app/docs
```

### Audio quality is poor

**Causes**:
- Low microphone gain
- Background noise
- Sample rate mismatch

**Fixes**:
```bash
# Increase microphone gain
alsamixer

# Test different sample rates
client = VoiceClient(sample_rate_hz=48000)

# Add noise cancellation
sudo apt-get install pulseaudio
```

### High latency (>10s response time)

**Causes**:
- Slow TTS provider
- Network latency
- Device overload

**Fixes**:
```python
# Use streaming TTS (future feature)
client.update_config(capabilities={"streaming": True})

# Use ElevenLabs for faster TTS
client.update_config(tts_provider="elevenlabs")

# Pre-warm connections
client.load_config()
```

### Device not persisting configuration

**Cause**: In-memory store resets on backend restart.

**Fix**: Implement Redis or Firestore storage (see TODO in `mqtt_bridge.py`).

```python
# In production, replace DeviceConfigStore with:
from google.cloud import firestore

db = firestore.Client()
device_ref = db.collection('devices').document(device_id)
device_ref.set(config_dict)
```

### MQTT messages not arriving (future MQTT integration)

**Cause**: Pub/Sub subscription not configured.

**Fix**: Set up Cloud Function or Cloud Run to consume Pub/Sub messages:

```python
# cloud_function.py
import functions_framework
import requests

@functions_framework.cloud_event
def process_mqtt_message(cloud_event):
    device_id = cloud_event.data['attributes']['device_id']
    payload = cloud_event.data['message']['data']
    
    # Forward to backend
    requests.post(
        f"https://your-backend.run.app/mqtt/devices/{device_id}/voice/query",
        json=payload
    )
```

---

## Cost Optimization

### 1. Use Self-Hosted TTS (Qwen)

Already configured. Saves ~$0.15 per 1000 characters vs ElevenLabs.

### 2. Batch Requests

For button-based toys, batch common queries:

```python
# Pre-generate common responses
CACHED_RESPONSES = {
    "help": client.synthesize_speech_sync("How can I help you?"),
    "repeat": "...",
}
```

### 3. Local Voice Activity Detection (VAD)

Reduce unnecessary STT calls:

```bash
pip install webrtcvad
```

```python
import webrtcvad

vad = webrtcvad.Vad(3)  # Aggressiveness 0-3
if vad.is_speech(audio_chunk, sample_rate):
    # Only send to backend if speech detected
    response = client.transcribe_audio_sync(audio)
```

### 4. Edge Inference (Advanced)

Run lightweight models on RPi 4/5:

```bash
# Install TensorFlow Lite
pip install tflite-runtime

# Use local STT for keyword detection
# Only send full query to cloud if keyword detected
```

---

## Next Steps

1. **Test with real hardware**: Run examples on RPi
2. **Add authentication**: Implement device API keys
3. **Enable true MQTT**: Set up GCP Pub/Sub integration
4. **Build fleet management**: Dashboard for monitoring devices
5. **Add streaming TTS**: Reduce latency for long responses
6. **Implement wake word**: Add "Hey SmartE" activation
7. **Create custom toys**: Use examples as templates

---

## Support

- **Documentation**: See `docs/MQTT_IOT_ARCHITECTURE.md`
- **Examples**: See `raspberry_pi/examples/`
- **API Reference**: https://your-backend.run.app/docs
- **Issues**: Open GitHub issue with logs and device config

## Appendix: Quick Reference

### Common Device IDs

- `rpi-edu-{number}` - Education toys
- `rpi-story-{number}` - Story narrator toys
- `rpi-button-{number}` - Button-based toys
- `rpi-recorder-{number}` - Recording toys

### Supported Domains

- `education` - CBSE education chatbot
- `wellbeing` - Mental health and wellness
- `sustainability` - Environmental topics
- `global-citizenship` - Global awareness
- `entrepreneurship` - Business skills
- `emotional-intelligence` - EQ development
- `financial-literacy` - Money management
- `design-thinking` - Creative problem solving
- `digital-literacy` - Tech skills
- `religious` - Religious education

### Supported Languages

See main README for complete list. Most common:
- `hi-IN` - Hindi
- `ta-IN` - Tamil
- `te-IN` - Telugu
- `bn-IN` - Bengali
- `mr-IN` - Marathi
- `en-IN` - Indian English

### TTS Voices

Format: `indic-{lang}-{gender}`

Examples:
- `indic-hindi-female`
- `indic-tamil-male`
- `indic-telugu-female`
- `indic-bengali-male`
- `indic-english-female`
