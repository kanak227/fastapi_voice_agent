# Domain Bot Quick Reference

## 🎯 Simple Answer: How to Use Any Domain Bot

### Step 1: Register Your Device with a Domain

```python
from mqtt_voice_client import VoiceClient

client = VoiceClient(
    device_id="your-device-id",
    api_url="https://your-backend.run.app",
    language="hi-IN",
)

# Choose your domain here ↓
client.register_device(
    domain="education",  # ← Change this to any domain
    tts_voice="indic-hindi-female",
)
```

### Step 2: Use It!

```python
# All queries now go to that domain bot automatically
response = client.text_interaction("Your question here")
```

**That's it!** The domain is saved in your device config, so you don't need to specify it again.

---

## 📚 All 10 Available Domains

| Domain | Description | Example Question |
|--------|-------------|------------------|
| `education` | CBSE SmartE bot | "भारत की राजधानी क्या है?" |
| `wellbeing` | Mental health | "I feel stressed today" |
| `financial-literacy` | Money skills | "बचत क्या है?" |
| `entrepreneurship` | Business skills | "How to start a business?" |
| `sustainability` | Environment | "What is climate change?" |
| `emotional-intelligence` | EQ development | "How to be more empathetic?" |
| `design-thinking` | Creative problem solving | "What is design thinking?" |
| `digital-literacy` | AI & tech skills | "What is artificial intelligence?" |
| `global-citizenship` | Global awareness | "What is global citizenship?" |
| `religious` | Religious education | "What are core moral values?" |

---

## 🔄 Switching Domains

### Change Domain Anytime

```python
# Switch to Wellbeing bot
client.update_config(domain="wellbeing")
response = client.text_interaction("Help me relax")

# Switch to Finance bot
client.update_config(domain="financial-literacy")
response = client.text_interaction("Tell me about savings")
```

### Check Current Domain

```python
config = client.load_config()
print(f"Current domain: {config['domain']}")
```

---

## 🌐 REST API Examples

### Using cURL

```bash
# 1. Register device with a domain
curl -X POST https://your-backend.run.app/mqtt/devices/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "rpi-toy-001",
    "domain": "education",
    "language": "hi-IN",
    "tts_voice": "indic-hindi-female",
    "capabilities": {"stt": true, "tts": true, "chat": true}
  }'

# 2. Send text query (uses configured domain)
curl -X POST https://your-backend.run.app/mqtt/devices/rpi-toy-001/text/query \
  -H "Content-Type: application/json" \
  -d '{
    "text": "भारत की राजधानी क्या है?",
    "session_id": "session-123"
  }'

# 3. Update domain
curl -X PUT https://your-backend.run.app/mqtt/devices/rpi-toy-001/config \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "rpi-toy-001",
    "domain": "wellbeing"
  }'
```

---

## 💡 Common Scenarios

### Scenario 1: Education Toy (One Domain)

```python
# Setup once
client.register_device(domain="education", tts_voice="indic-hindi-female")

# Use forever
while True:
    response = client.voice_interaction()  # Always uses education bot
```

### Scenario 2: Multi-Purpose Toy (Multiple Domains)

```python
# Setup
client.register_device(domain="education")

# Switch based on user choice
user_choice = input("Topic? (1=Education, 2=Wellbeing, 3=Finance): ")

if user_choice == "1":
    client.update_config(domain="education")
elif user_choice == "2":
    client.update_config(domain="wellbeing")
elif user_choice == "3":
    client.update_config(domain="financial-literacy")

response = client.voice_interaction()
```

### Scenario 3: Button-Based Domain Selection

```python
import RPi.GPIO as GPIO

BUTTON_1 = 17  # Education
BUTTON_2 = 27  # Wellbeing
BUTTON_3 = 22  # Finance

while True:
    if GPIO.input(BUTTON_1) == GPIO.LOW:
        client.update_config(domain="education")
        response = client.text_interaction("Tell me something")
    
    elif GPIO.input(BUTTON_2) == GPIO.LOW:
        client.update_config(domain="wellbeing")
        response = client.text_interaction("Help me relax")
    
    elif GPIO.input(BUTTON_3) == GPIO.LOW:
        client.update_config(domain="financial-literacy")
        response = client.text_interaction("Tell me about money")
```

---

## 🎨 Language + Domain Combinations

### Hindi + Education
```python
client.register_device(
    domain="education",
    language="hi-IN",
    tts_voice="indic-hindi-female",
)
```

### Tamil + Wellbeing
```python
client.register_device(
    domain="wellbeing",
    language="ta-IN",
    tts_voice="indic-tamil-female",
)
```

### English + Finance
```python
client.register_device(
    domain="financial-literacy",
    language="en-IN",
    tts_voice="indic-english-male",
)
```

---

## ❓ FAQ

### Q: Can one device use multiple domains?
**A:** Yes! Use `client.update_config(domain="new-domain")` to switch.

### Q: How often can I switch domains?
**A:** Anytime! There's no limit.

### Q: Does switching domains affect conversation history?
**A:** Each domain has its own conversation context. Switching domains starts a fresh conversation with the new bot.

### Q: Can I use the same device ID for different domains?
**A:** Yes, but the device remembers the last domain you set. Better to use different device IDs for dedicated-purpose toys.

### Q: What if I don't specify a domain?
**A:** The system uses the default domain from your device config, or falls back to "education".

### Q: Can I have different languages for different domains?
**A:** Yes! Update both at once:
```python
client.update_config(domain="wellbeing", language="ta-IN", tts_voice="indic-tamil-female")
```

---

## 📖 Full Documentation

For complete examples and advanced usage, see:
- **Complete Guide**: `docs/MQTT_DOMAIN_BOT_USAGE.md`
- **Architecture**: `docs/MQTT_IOT_ARCHITECTURE.md`
- **Integration**: `docs/MQTT_INTEGRATION_GUIDE.md`
- **Quick Start**: `docs/MQTT_QUICK_START.md`

---

## 🚀 Quick Copy-Paste Templates

### Template 1: Education Bot
```python
from mqtt_voice_client import VoiceClient

client = VoiceClient("rpi-edu-001", "https://your-backend.run.app", "hi-IN")
client.register_device(domain="education", tts_voice="indic-hindi-female")
response = client.voice_interaction()
```

### Template 2: Wellbeing Bot
```python
from mqtt_voice_client import VoiceClient

client = VoiceClient("rpi-wellbeing-001", "https://your-backend.run.app", "en-IN")
client.register_device(domain="wellbeing", tts_voice="indic-english-female")
response = client.text_interaction("I feel stressed")
```

### Template 3: Multi-Domain Bot
```python
from mqtt_voice_client import VoiceClient

client = VoiceClient("rpi-multi-001", "https://your-backend.run.app", "hi-IN")
client.register_device(domain="education")

# Switch domains as needed
domains = ["education", "wellbeing", "financial-literacy"]
for domain in domains:
    client.update_config(domain=domain)
    response = client.text_interaction("Tell me something interesting")
```

---

## ✅ Summary

**To use any domain bot with MQTT endpoints:**

1. **Register** with `domain="your-choice"`
2. **Use normally** - all queries go to that domain
3. **Switch anytime** with `update_config(domain="new-choice")`

**That's all!** The domain is stored in the device configuration, so you don't need to specify it in every request.
