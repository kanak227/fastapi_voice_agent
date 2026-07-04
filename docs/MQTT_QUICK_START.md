# MQTT IoT Quick Start Guide

Get your first Raspberry Pi voice toy running in 15 minutes.

## What You Need

- Raspberry Pi (any model with audio)
- USB microphone (for voice input)
- Speaker or headphones
- Internet connection
- Your GCP backend URL

## 5-Step Setup

### Step 1: Deploy Backend (2 minutes)

```bash
cd deployment/gcp
gcloud builds submit --config=cloudbuild.yaml
```

Get your backend URL:
```bash
gcloud run services describe multi-bot-server --region=us-central1 --format='value(status.url)'
```

### Step 2: Setup Raspberry Pi (5 minutes)

```bash
# Update system
sudo apt-get update
sudo apt-get install -y python3 python3-pip portaudio19-dev

# Copy client library to RPi
scp -r raspberry_pi/ pi@your-rpi-ip:~/

# SSH to RPi
ssh pi@your-rpi-ip

# Install dependencies
cd ~/raspberry_pi/mqtt_voice_client
pip3 install -r requirements.txt
```

### Step 3: Test Audio (2 minutes)

```bash
# Test microphone
arecord -d 5 test.wav
aplay test.wav

# Adjust volume if needed
alsamixer
```

### Step 4: Configure Device (2 minutes)

Edit `examples/full_voice_toy.py`:

```python
# Change these lines:
DEVICE_ID = "rpi-my-toy-001"  # Unique ID for your device
API_URL = "https://your-backend-url.run.app"  # Your GCP URL
LANGUAGE = "hi-IN"  # Your language (hi-IN, ta-IN, en-IN, etc.)
TTS_VOICE = "indic-hindi-female"  # Your voice preference
DOMAIN = "education"  # education, wellbeing, etc.
```

### Step 5: Run! (1 minute)

```bash
cd ~/raspberry_pi/examples
python3 full_voice_toy.py
```

Press Enter, speak for 5 seconds, and hear the response!

## What Happens?

```
You speak → RPi records → Backend transcribes → LLM generates response → TTS synthesizes → RPi plays audio
```

## Common Issues

### "No audio backend available"

```bash
pip3 install sounddevice numpy
```

### "Device registration failed"

Check your backend URL:
```bash
curl https://your-backend-url.run.app/health
```

### "No speech detected"

- Speak louder
- Adjust microphone gain: `alsamixer`
- Check mic is selected: `arecord -l`

### High latency

This is normal for first request (~10s). Subsequent requests are faster (~3-5s).

## Different Toy Types

### 1. Full Voice (Current Setup)

Microphone + Speaker + Chat

```bash
python3 full_voice_toy.py
```

### 2. Button Toy

No microphone, just buttons + Speaker

```bash
python3 button_toy.py
```

Edit button mappings in the script.

### 3. TTS-Only Narrator

Just reads text aloud

```bash
python3 tts_only_toy.py
```

## Auto-Start on Boot

```bash
sudo nano /etc/systemd/system/voice-toy.service
```

```ini
[Unit]
Description=Voice Toy
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/raspberry_pi/examples
ExecStart=/usr/bin/python3 /home/pi/raspberry_pi/examples/full_voice_toy.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable voice-toy.service
sudo systemctl start voice-toy.service
```

## Customization

### Change Language

```python
client = VoiceClient(
    device_id="rpi-toy-001",
    api_url="https://your-backend.run.app",
    language="ta-IN",  # Tamil
)

client.register_device(
    tts_voice="indic-tamil-female",
)
```

### Change Domain

```python
client.register_device(
    domain="wellbeing",  # Mental health bot
)
```

### Available Domains

- `education` - CBSE education
- `wellbeing` - Mental health
- `sustainability` - Environment
- `financial-literacy` - Money skills
- `entrepreneurship` - Business
- `emotional-intelligence` - EQ
- `digital-literacy` - Tech skills
- `design-thinking` - Creativity
- `global-citizenship` - Global topics
- `religious` - Religious education

### Available Languages

Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Odia, Assamese, Bodo, Manipuri, Rajasthani, English (Indian & US)

### Available Voices

Format: `indic-{language}-{gender}`

Examples:
- `indic-hindi-female`
- `indic-hindi-male`
- `indic-tamil-female`
- `indic-tamil-male`
- `indic-telugu-female`
- `indic-bengali-male`
- `indic-english-female`

List all voices:
```bash
curl https://your-backend.run.app/voice/voices?tts_provider=qwen
```

## Next Steps

1. **Test different toy types** - Try button_toy.py and tts_only_toy.py
2. **Build custom toy** - Use examples as templates
3. **Add hardware buttons** - Connect GPIO buttons for interactions
4. **Deploy multiple devices** - Each needs unique device_id
5. **Monitor usage** - Check logs and device configs
6. **Production hardening** - Set up auto-start service

## Full Documentation

- Architecture: `docs/MQTT_IOT_ARCHITECTURE.md`
- Integration Guide: `docs/MQTT_INTEGRATION_GUIDE.md`
- Client Library: `raspberry_pi/README.md`
- Examples: `raspberry_pi/examples/`

## Getting Help

1. Check logs: `sudo journalctl -u voice-toy.service -f`
2. Test backend: `curl https://your-backend.run.app/health`
3. View device config: `curl https://your-backend.run.app/mqtt/devices/your-device-id/config`
4. Open GitHub issue with logs and config

## Cost

**Per device per month** (100 interactions/day):
- STT (Deepgram): ~$0.60
- TTS (Qwen self-hosted): $0.00
- LLM (Gemini): ~$0.30
- **Total: ~$0.90/device/month**

**Backend infrastructure**:
- Cloud Run: ~$50-100/month (1000+ devices)
- Pub/Sub: ~$40/month (future MQTT)
- Redis/Firestore: ~$10-30/month

## Hardware Recommendations

### Budget (~$50)
- Raspberry Pi Zero 2 W
- USB microphone
- 3.5mm speaker

### Recommended (~$100)
- Raspberry Pi 4 (2GB)
- I2S MEMS microphone
- I2S audio HAT + speaker

### Premium (~$150)
- Raspberry Pi 5 (4GB)
- ReSpeaker 2-Mic HAT
- Bluetooth speaker
- Custom enclosure

## Success Checklist

- [ ] Backend deployed and accessible
- [ ] RPi connected to internet
- [ ] Audio working (mic and speaker)
- [ ] Python client installed
- [ ] Device registered
- [ ] First voice interaction successful
- [ ] Response played through speaker
- [ ] Auto-start configured (optional)

## You're Ready!

Your IoT voice toy is now connected to the full GCP backend with:
- ✅ Speech-to-Text (Deepgram)
- ✅ LLM Chat (Gemini)
- ✅ Text-to-Speech (Qwen + FastPitch)
- ✅ Multi-language support
- ✅ Domain-specific knowledge
- ✅ Session management
- ✅ Conversation memory

Start building amazing voice toys! 🎉
