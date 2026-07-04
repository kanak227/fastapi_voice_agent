# MQTT IoT Documentation Index

Complete documentation for the Raspberry Pi MQTT IoT voice toy system.

## 📚 Documentation Overview

This folder contains all documentation for building and deploying IoT voice toys that connect to your GCP-based chatbot backend.

## 🚀 Getting Started

**New to the system?** Start here:

1. **[Quick Start Guide](MQTT_QUICK_START.md)** ⭐
   - 15-minute setup
   - Get your first toy working fast
   - Perfect for beginners

2. **[Domain Bot Quick Reference](DOMAIN_BOT_QUICK_REFERENCE.md)** ⭐
   - **Most important: How to use any domain bot**
   - Simple copy-paste examples
   - FAQ and common scenarios

## 📖 Complete Guides

### For Developers

3. **[Architecture Overview](MQTT_IOT_ARCHITECTURE.md)**
   - System design and components
   - Message flow and protocols
   - Security and cost analysis
   - Implementation phases

4. **[Integration Guide](MQTT_INTEGRATION_GUIDE.md)**
   - Step-by-step setup instructions
   - Backend deployment
   - Raspberry Pi configuration
   - Production deployment
   - Troubleshooting

5. **[Domain Bot Usage Guide](MQTT_DOMAIN_BOT_USAGE.md)** ⭐
   - **Complete guide for using all 10 domain bots**
   - REST API examples
   - Multi-domain toys
   - Working code examples

6. **[Flow Diagrams](MQTT_FLOW_DIAGRAM.md)**
   - Visual system flows
   - Domain routing explained
   - Button-based selection
   - Complete system overview

## 🎯 Quick Answers

### How do I use a specific domain bot?

**Simple answer:**

```python
# Set domain during registration
client.register_device(domain="education")

# All queries now go to education bot
response = client.voice_interaction()
```

See: **[Domain Bot Quick Reference](DOMAIN_BOT_QUICK_REFERENCE.md)**

### What domains are available?

1. `education` - CBSE education (SmartE)
2. `wellbeing` - Mental health support
3. `financial-literacy` - Money skills
4. `entrepreneurship` - Business guidance
5. `sustainability` - Environmental topics
6. `emotional-intelligence` - EQ development
7. `design-thinking` - Creative problem solving
8. `digital-literacy` - AI and tech skills
9. `global-citizenship` - Global awareness
10. `religious` - Religious education

See: **[Domain Bot Quick Reference](DOMAIN_BOT_QUICK_REFERENCE.md)**

### How do I switch domains?

```python
# Switch anytime
client.update_config(domain="wellbeing")
```

See: **[Domain Bot Usage Guide](MQTT_DOMAIN_BOT_USAGE.md)**

### Where do I find code examples?

See: **`../raspberry_pi/examples/`**
- `full_voice_toy.py` - Complete voice interaction
- `tts_only_toy.py` - Text-to-speech narrator
- `button_toy.py` - Hardware button interface

## 📋 Document Purpose Summary

| Document | Purpose | For |
|----------|---------|-----|
| **Quick Start** | Get running in 15 minutes | Beginners |
| **Domain Quick Ref** | Use any domain bot | Everyone ⭐ |
| **Architecture** | Understand system design | Architects |
| **Integration** | Deploy to production | DevOps |
| **Domain Usage** | Complete domain bot guide | Developers ⭐ |
| **Flow Diagrams** | Visualize system flows | Visual learners |

## 🎓 Learning Paths

### Path 1: "I just want it to work"
1. [Quick Start Guide](MQTT_QUICK_START.md)
2. [Domain Bot Quick Reference](DOMAIN_BOT_QUICK_REFERENCE.md)
3. Run examples in `../raspberry_pi/examples/`

### Path 2: "I want to understand the system"
1. [Architecture Overview](MQTT_IOT_ARCHITECTURE.md)
2. [Flow Diagrams](MQTT_FLOW_DIAGRAM.md)
3. [Integration Guide](MQTT_INTEGRATION_GUIDE.md)

### Path 3: "I want to build custom toys"
1. [Quick Start Guide](MQTT_QUICK_START.md)
2. [Domain Bot Usage Guide](MQTT_DOMAIN_BOT_USAGE.md)
3. [Integration Guide](MQTT_INTEGRATION_GUIDE.md)
4. Study `../raspberry_pi/examples/`

### Path 4: "I need to deploy to production"
1. [Architecture Overview](MQTT_IOT_ARCHITECTURE.md)
2. [Integration Guide](MQTT_INTEGRATION_GUIDE.md)
3. [Domain Bot Usage Guide](MQTT_DOMAIN_BOT_USAGE.md)

## 🔧 API Reference

See: **`../raspberry_pi/README.md`** for complete Python client library API reference

## 📦 What's in This Repository

```
MAIN/
├── docs/                          ← You are here
│   ├── README.md                  ← This file
│   ├── MQTT_QUICK_START.md        ← Start here!
│   ├── DOMAIN_BOT_QUICK_REFERENCE.md ← Domain bot guide
│   ├── MQTT_DOMAIN_BOT_USAGE.md   ← Complete domain examples
│   ├── MQTT_IOT_ARCHITECTURE.md   ← System design
│   ├── MQTT_INTEGRATION_GUIDE.md  ← Deployment guide
│   └── MQTT_FLOW_DIAGRAM.md       ← Visual flows
│
├── raspberry_pi/                  ← Client library & examples
│   ├── mqtt_voice_client/         ← Python library
│   │   ├── client.py              ← Main VoiceClient class
│   │   ├── audio.py               ← Audio recording/playback
│   │   └── requirements.txt       ← Dependencies
│   ├── examples/                  ← Working examples
│   │   ├── full_voice_toy.py      ← Full voice assistant
│   │   ├── tts_only_toy.py        ← Story narrator
│   │   └── button_toy.py          ← Button-based toy
│   ├── setup.sh                   ← Automated setup script
│   └── README.md                  ← API reference
│
└── fastapi_server/                ← Backend service
    └── app/routers/
        └── mqtt_bridge.py         ← MQTT bridge service
```

## 🎯 Common Tasks

### Task: Register a new device

```python
from mqtt_voice_client import VoiceClient

client = VoiceClient(
    device_id="rpi-toy-001",
    api_url="https://your-backend.run.app",
    language="hi-IN",
)

client.register_device(
    domain="education",
    tts_voice="indic-hindi-female",
)
```

See: [Quick Start](MQTT_QUICK_START.md) or [Domain Quick Ref](DOMAIN_BOT_QUICK_REFERENCE.md)

### Task: Switch to a different domain bot

```python
client.update_config(domain="wellbeing")
```

See: [Domain Quick Ref](DOMAIN_BOT_QUICK_REFERENCE.md)

### Task: Build a multi-domain toy

See: [Domain Bot Usage Guide](MQTT_DOMAIN_BOT_USAGE.md) - Multi-Domain Toy section

### Task: Deploy to production

See: [Integration Guide](MQTT_INTEGRATION_GUIDE.md) - Production Deployment section

### Task: Add hardware buttons

See: `../raspberry_pi/examples/button_toy.py`

### Task: Troubleshoot issues

See: [Integration Guide](MQTT_INTEGRATION_GUIDE.md) - Troubleshooting section

## 🌟 Key Features

✅ **10 Domain Bots** - Education, Wellbeing, Finance, Entrepreneurship, Sustainability, Emotional Intelligence, Design Thinking, Digital Literacy, Global Citizenship, Religious

✅ **16 Languages** - Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Odia, Assamese, Bodo, Manipuri, Rajasthani, English (Indian & US)

✅ **18 TTS Voices** - AI4Bharat FastPitch voices (male & female for each language)

✅ **Modular Design** - STT-only, TTS-only, Full voice, Button-based, Custom configurations

✅ **Low Cost** - ~$1.20/device/month

✅ **Production Ready** - Error handling, auto-reconnect, logging

## 💡 Pro Tips

1. **Start simple**: Use Quick Start guide first, understand later
2. **Domain = Bot**: Setting domain in device config determines which bot answers
3. **One config, many queries**: Set domain once, use forever
4. **Switch anytime**: Change domain with `update_config()`
5. **Different toys, different domains**: Use dedicated device_id for each purpose
6. **Read examples**: Working code in `../raspberry_pi/examples/`

## 🆘 Getting Help

1. Check **[FAQ in Domain Quick Ref](DOMAIN_BOT_QUICK_REFERENCE.md)**
2. Read **[Troubleshooting in Integration Guide](MQTT_INTEGRATION_GUIDE.md)**
3. Study examples in `../raspberry_pi/examples/`
4. Check device config: `curl https://your-backend.run.app/mqtt/devices/{device_id}/config`
5. View backend logs in GCP Cloud Run console

## 📞 Support

- **Documentation Issues**: Open GitHub issue
- **Bug Reports**: Include device config, logs, and request/response
- **Feature Requests**: Describe use case and expected behavior
- **Questions**: Check existing docs first, then ask in GitHub discussions

## 🚀 Next Steps

1. **Read**: [Quick Start Guide](MQTT_QUICK_START.md)
2. **Learn**: [Domain Bot Quick Reference](DOMAIN_BOT_QUICK_REFERENCE.md)
3. **Deploy**: Follow [Integration Guide](MQTT_INTEGRATION_GUIDE.md)
4. **Build**: Modify examples in `../raspberry_pi/examples/`
5. **Share**: Contribute improvements back to the project

---

## Summary

This MQTT IoT system connects Raspberry Pi voice toys to your existing GCP backend with support for **10 domain bots**, **16 languages**, and **flexible configurations**. The system is:

- **Simple to use**: One line to set domain, all queries go there
- **Well documented**: 6 comprehensive guides + API reference
- **Production ready**: Tested, error-handled, scalable
- **Cost effective**: ~$1.20/device/month

**Start here**: [Quick Start Guide](MQTT_QUICK_START.md) → [Domain Bot Quick Reference](DOMAIN_BOT_QUICK_REFERENCE.md)

Happy building! 🎉
