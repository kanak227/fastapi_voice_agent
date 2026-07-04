# MQTT IoT System Flow Diagrams

Visual representation of how domain bots work with MQTT endpoints.

## Basic Flow: Device → Domain Bot → Response

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Register Device with Domain                         │
└─────────────────────────────────────────────────────────────┘

    Raspberry Pi Device
         │
         │ POST /mqtt/devices/register
         │ {
         │   "device_id": "rpi-toy-001",
         │   "domain": "education",  ← Choose domain
         │   "language": "hi-IN",
         │   "tts_voice": "indic-hindi-female"
         │ }
         ↓
    Backend MQTT Bridge
         │
         │ Stores config in memory/Redis/Firestore:
         │ • device_id: rpi-toy-001
         │ • domain: education ✓
         │ • language: hi-IN
         │ • tts_voice: indic-hindi-female
         ↓
    ✅ Registration Complete!

┌─────────────────────────────────────────────────────────────┐
│ Step 2: Use Device (All queries go to configured domain)    │
└─────────────────────────────────────────────────────────────┘

    User speaks to device
         │
         ↓
    RPi records audio (5 seconds)
         │
         │ POST /mqtt/devices/rpi-toy-001/voice/query
         │ {
         │   "audio_b64": "base64-encoded-audio...",
         │   "session_id": "session-123"
         │ }
         ↓
    Backend MQTT Bridge
         │
         ├─ Loads device config
         │  → domain: education ✓
         │  → language: hi-IN
         │  → tts_voice: indic-hindi-female
         │
         ├─ [1] Deepgram STT
         │  → Transcript: "भारत की राजधानी क्या है?"
         │
         ├─ [2] Routes to EDUCATION Domain Bot ✓
         │  → Bot processes question
         │  → Response: "भारत की राजधानी नई दिल्ली है।"
         │
         └─ [3] Qwen TTS (FastPitch)
            → Synthesizes Hindi audio
            → Returns WAV file (base64)
         
         ↓
    Response sent to RPi
         │
         │ {
         │   "success": true,
         │   "data": {
         │     "transcript": "भारत की राजधानी क्या है?",
         │     "response_text": "भारत की राजधानी नई दिल्ली है।",
         │     "audio_b64": "UklGRi4A...",
         │     "voice": "indic-hindi-female"
         │   }
         │ }
         ↓
    RPi plays audio response
         │
         ↓
    User hears: "भारत की राजधानी नई दिल्ली है।" 🔊
```

## Domain Routing: How Backend Chooses the Right Bot

```
┌───────────────────────────────────────────────────────────────┐
│              Incoming Request from Device                      │
│          POST /mqtt/devices/{device_id}/voice/query           │
└───────────────────────────────────────────────────────────────┘
                            │
                            ↓
                  Load Device Config
                            │
                   ┌────────┴────────┐
                   │  Device Config   │
                   │  domain: ?       │
                   └────────┬────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ↓                   ↓                   ↓
   domain =           domain =              domain =
  "education"       "wellbeing"         "financial-literacy"
        │                   │                   │
        ↓                   ↓                   ↓
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Education Bot │   │ Wellbeing Bot │   │  Finance Bot  │
│  (SmartE)     │   │ (Mental Health)   │ (Money Skills)│
│               │   │               │   │               │
│ Knowledge:    │   │ Knowledge:    │   │ Knowledge:    │
│ • CBSE topics │   │ • Stress mgmt │   │ • Savings     │
│ • Science     │   │ • Mindfulness │   │ • Budgeting   │
│ • Math        │   │ • Emotions    │   │ • Investing   │
│ • History     │   │ • Relaxation  │   │ • Banking     │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ↓
                    Response Generated
                            │
                            ↓
                      TTS Synthesis
                            │
                            ↓
                   Response to Device
```

## All 10 Domain Bots Available

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Device                               │
│                  (rpi-toy-001)                               │
│                                                              │
│             Configure with ANY domain:                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
       ↓               ↓               ↓
   Education       Wellbeing      Financial
   (SmartE)       (Mental Health)  Literacy
   CBSE topics    Stress, relax    Money skills
       │               │               │
       ↓               ↓               ↓
   Entrepreneur    Sustainability  Emotional
   (Business)      (Environment)   Intelligence
   Startups        Climate, green  EQ, empathy
       │               │               │
       ↓               ↓               ↓
   Design          Digital         Global
   Thinking        Literacy        Citizenship
   Creativity      AI, tech        World topics
       │               │               │
       ↓               ↓               ↓
   Religious
   (Spiritual)
   Faith, values
```

## Switching Domains: Multi-Purpose Toy

```
┌─────────────────────────────────────────────────────────────┐
│              Multi-Purpose Toy Workflow                      │
└─────────────────────────────────────────────────────────────┘

Initial Setup:
    client.register_device(domain="education")
    
    Config Stored:
    ┌────────────────────────┐
    │ device_id: rpi-toy-001 │
    │ domain: education ✓    │
    └────────────────────────┘

User Query 1:
    "Tell me about science"
         ↓
    Uses: Education Bot ✓
    Response: Science explanation...

User switches topic:
    client.update_config(domain="wellbeing")
    
    Config Updated:
    ┌────────────────────────┐
    │ device_id: rpi-toy-001 │
    │ domain: wellbeing ✓    │  ← Changed
    └────────────────────────┘

User Query 2:
    "Help me relax"
         ↓
    Uses: Wellbeing Bot ✓
    Response: Relaxation guidance...

User switches again:
    client.update_config(domain="financial-literacy")
    
    Config Updated:
    ┌────────────────────────┐
    │ device_id: rpi-toy-001 │
    │ domain: financial-lit ✓│  ← Changed
    └────────────────────────┘

User Query 3:
    "What is savings?"
         ↓
    Uses: Finance Bot ✓
    Response: Savings explanation...
```

## Button-Based Domain Selection

```
┌─────────────────────────────────────────────────────────────┐
│           Hardware Button Toy (3 buttons)                    │
└─────────────────────────────────────────────────────────────┘

    ┌─────────┐  ┌─────────┐  ┌─────────┐
    │Button 1 │  │Button 2 │  │Button 3 │
    │ (GPIO17)│  │ (GPIO27)│  │ (GPIO22)│
    └────┬────┘  └────┬────┘  └────┬────┘
         │            │            │
         │            │            │
  [Education]    [Wellbeing]   [Finance]
         │            │            │
         └────────────┼────────────┘
                      ↓
              Raspberry Pi Logic:
              
              if Button 1 pressed:
                  update_config(domain="education")
                  query("Tell me about science")
              
              elif Button 2 pressed:
                  update_config(domain="wellbeing")
                  query("Help me relax")
              
              elif Button 3 pressed:
                  update_config(domain="financial-literacy")
                  query("Tell me about money")
                      ↓
              Current domain stored in config
                      ↓
              Next query uses that domain
```

## Text Query Flow (Simpler, No STT)

```
┌─────────────────────────────────────────────────────────────┐
│              Text Query (Button or External Input)           │
└─────────────────────────────────────────────────────────────┘

    User presses button or external app sends text
         │
         │ POST /mqtt/devices/rpi-toy-001/text/query
         │ {
         │   "text": "भारत की राजधानी क्या है?",
         │   "session_id": "session-123"
         │ }
         ↓
    Backend MQTT Bridge
         │
         ├─ Load config → domain: education ✓
         │
         ├─ [No STT needed, text already provided]
         │
         ├─ Route to Education Bot
         │  → Response: "भारत की राजधानी नई दिल्ली है।"
         │
         └─ TTS Synthesis
            → Audio: base64-encoded WAV
         
         ↓
    Response to Device
         │
         │ {
         │   "response_text": "...",
         │   "audio_b64": "..."
         │ }
         ↓
    Play audio through speaker 🔊
```

## TTS-Only Flow (No Bot, No STT)

```
┌─────────────────────────────────────────────────────────────┐
│              TTS-Only (Story Narrator)                       │
└─────────────────────────────────────────────────────────────┘

    External app provides pre-written text
         │
         │ POST /mqtt/devices/rpi-narrator-001/synthesize
         │ {
         │   "text": "Once upon a time...",
         │   "language": "ta-IN",
         │   "voice": "indic-tamil-male"
         │ }
         ↓
    Backend MQTT Bridge
         │
         ├─ [No STT, No Bot]
         │
         └─ TTS Synthesis only
            → Qwen + FastPitch
            → Audio: Tamil male voice
         
         ↓
    Response
         │
         │ {
         │   "audio_b64": "...",
         │   "mime_type": "audio/wav",
         │   "voice": "indic-tamil-male"
         │ }
         ↓
    Play story audio 🔊
```

## Complete System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  COMPLETE MQTT IOT SYSTEM                    │
└─────────────────────────────────────────────────────────────┘

         Raspberry Pi Devices (Any Domain)
    ┌────────┬────────┬────────┬────────┬────────┐
    │Edu Toy │Well Toy│Finance │Story   │Custom  │
    │Hindi   │English │Hindi   │Tamil   │Multi   │
    └───┬────┴───┬────┴───┬────┴───┬────┴───┬────┘
        │        │        │        │        │
        └────────┴────────┴────────┴────────┘
                      │
                      ↓
        ┌─────────────────────────────┐
        │   MQTT Bridge Service       │
        │   /mqtt/* endpoints         │
        │                             │
        │   • Device registration     │
        │   • Config management       │
        │   • Request routing         │
        └─────────────┬───────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ↓             ↓             ↓
   ┌────────┐   ┌────────┐   ┌────────┐
   │  STT   │   │  BOTS  │   │  TTS   │
   │Deepgram   │10 Domains   │ Qwen   │
   └────────┘   └────┬───┘   └────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ↓            ↓            ↓
   Education    Wellbeing    Finance
   Religious    Sustain.     Emotion
   Design       Digital      Global
   Entrepreneur (10 total)
                     │
                     ↓
              Response with
              Domain-specific
              Knowledge
```

## Key Takeaway

```
┌─────────────────────────────────────────────────────────────┐
│                    SIMPLE TRUTH                              │
│                                                              │
│  1. Register device with a domain                           │
│     client.register_device(domain="education")              │
│                                                              │
│  2. Backend stores: device → domain mapping                 │
│                                                              │
│  3. All queries from that device go to that domain bot      │
│                                                              │
│  4. Want to change? Just update config                      │
│     client.update_config(domain="wellbeing")                │
│                                                              │
│  That's it! No domain in every request needed.              │
└─────────────────────────────────────────────────────────────┘
```

## Real-World Example

```
Scenario: School has 3 toys

Toy 1 (Education, Hindi):
    device_id: "school-edu-001"
    domain: "education"
    language: "hi-IN"
    → Always answers CBSE education questions

Toy 2 (Wellbeing, English):
    device_id: "school-well-001"
    domain: "wellbeing"
    language: "en-IN"
    → Always provides mental health support

Toy 3 (Multi-purpose, Hindi):
    device_id: "school-multi-001"
    domain: "education" (default)
    → Can switch between domains with buttons
    → Button 1: education
    → Button 2: wellbeing
    → Button 3: financial-literacy

Each toy remembers its domain in the backend config!
```
