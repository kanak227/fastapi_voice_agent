# Toy vs Frontend: How They're The Same

## TL;DR - YES, Toys Can Use Frontend Endpoints Directly!

**You're absolutely right!** The toys **CAN use the exact same `/agent/stream` and `/agent/ws` endpoints** that your frontend uses. There's **NO need for separate MQTT endpoints** if you want the toys to work exactly like the frontend.

## Why We Created Two Options

### Option 1: Use Existing Frontend Endpoints (SIMPLER) ✅

**Toys use the SAME endpoints as your web frontend:**
- `/agent/stream` - HTTP streaming (same as frontend)
- `/agent/ws` - WebSocket (same as frontend)
- `/voice/transcribe` - STT (same as frontend)
- `/voice/synthesize` - TTS (same as frontend)

**This is SIMPLER and uses your existing, tested code!**

### Option 2: Use New MQTT Endpoints (MORE FEATURES)

**Why we created `/mqtt/*` endpoints:**
- Device management (registration, config)
- Per-device settings stored on backend
- Built-in device capabilities (STT/TTS/Chat combos)
- Simplified API for embedded devices
- Future: True MQTT protocol support

**But Option 1 is perfectly fine for most use cases!**

---

## Complete Comparison

### Frontend Flow (Web Browser)

```
User clicks button → Frontend records audio → POST /agent/stream
                                                   ↓
                                    Backend processes (STT + Chat + TTS)
                                                   ↓
                                    SSE stream back to frontend
                                                   ↓
                            Frontend plays audio chunks as they arrive
```

### Toy Flow - Option 1 (Use Frontend Endpoints) ⭐ RECOMMENDED

```
User speaks → Toy records audio → POST /agent/stream (SAME ENDPOINT!)
                                          ↓
                       Backend processes (STT + Chat + TTS)
                                          ↓
                       SSE stream back to toy (SAME AS FRONTEND!)
                                          ↓
                       Toy plays audio chunks as they arrive
```

**IT'S EXACTLY THE SAME! No separate endpoints needed!**

### Toy Flow - Option 2 (Use MQTT Endpoints)

```
User speaks → Toy records audio → POST /mqtt/devices/{id}/voice/query
                                          ↓
                       MQTT Bridge loads device config
                                          ↓
                       Calls /agent/stream internally
                                          ↓
                       Returns complete response (not streaming)
                                          ↓
                       Toy plays full audio
```

---

## How Toys Can Work EXACTLY Like Frontend

### Frontend Code (Next.js)

```javascript
// Frontend voice interaction
async function handleVoiceQuery(audioBlob) {
  // Convert to base64
  const audioBase64 = await blobToBase64(audioBlob);
  
  // Call backend (SAME endpoint as toy can use!)
  const response = await fetch('/agent/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-Id': 'tenant-demo',
    },
    body: JSON.stringify({
      session_id: sessionId,
      input_type: 'audio',
      audio: {
        audio_b64: audioBase64,
        sample_rate_hz: 16000,
      },
      domain: 'education',  // Choose domain
      language: 'hi-IN',
      output_audio: true,
      tts_provider: 'qwen',
      tts_voice: 'indic-hindi-female',
    }),
  });
  
  // Read SSE stream
  const reader = response.body.getReader();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    // Parse SSE events
    const events = parseSSE(value);
    for (const event of events) {
      if (event.event === 'audio') {
        // Play audio chunk
        playAudio(event.data.audio_b64);
      }
    }
  }
}
```

### Toy Code (Python) - Using SAME Endpoint!

```python
import requests
import base64
import json

def handle_voice_query(audio_bytes):
    # Convert to base64
    audio_b64 = base64.b64encode(audio_bytes).decode('ascii')
    
    # Call backend (SAME endpoint as frontend!)
    response = requests.post(
        'https://your-backend.run.app/agent/stream',
        headers={
            'Content-Type': 'application/json',
            'X-Tenant-Id': 'tenant-demo',
        },
        json={
            'session_id': 'session-123',
            'input_type': 'audio',
            'audio': {
                'audio_b64': audio_b64,
                'sample_rate_hz': 16000,
            },
            'domain': 'education',  # Choose domain
            'language': 'hi-IN',
            'output_audio': True,
            'tts_provider': 'qwen',
            'tts_voice': 'indic-hindi-female',
        },
        stream=True,  # SSE stream
    )
    
    # Read SSE stream (SAME as frontend!)
    for line in response.iter_lines():
        if line.startswith(b'event: audio'):
            # Next line has data
            data_line = next(response.iter_lines())
            data = json.loads(data_line.decode()[6:])  # Skip "data: "
            
            # Play audio chunk
            play_audio(base64.b64decode(data['audio_b64']))
```

**IT'S THE SAME CODE LOGIC!**

---

## Auto Voice Capture Like Frontend

### How Frontend Handles It

Your frontend likely has:

1. **Button press** → Start recording
2. **User speaks** → Browser captures audio
3. **Button release** or **Silence detection** → Stop recording
4. **Send to backend** → POST /agent/stream
5. **Receive response** → Play audio chunks

### How Toy Can Handle It THE SAME WAY

```python
#!/usr/bin/env python3
"""
Toy that works EXACTLY like frontend
Uses same /agent/stream endpoint
"""

import requests
import base64
import json
import sounddevice as sd
import numpy as np
from queue import Queue
import threading

class VoiceToy:
    def __init__(self, api_url, domain="education", language="hi-IN"):
        self.api_url = api_url
        self.domain = domain
        self.language = language
        self.session_id = f"toy-session-{int(time.time())}"
        self.recording = False
        self.audio_queue = Queue()
    
    def start_recording(self):
        """Start recording (like frontend button press)"""
        self.recording = True
        self.audio_queue = Queue()
        
        def callback(indata, frames, time, status):
            if self.recording:
                self.audio_queue.put(indata.copy())
        
        # Start audio stream
        self.stream = sd.InputStream(
            samplerate=16000,
            channels=1,
            dtype='int16',
            callback=callback,
        )
        self.stream.start()
        print("🎤 Recording... (Press Enter to stop)")
    
    def stop_recording(self):
        """Stop recording (like frontend button release)"""
        self.recording = False
        self.stream.stop()
        self.stream.close()
        
        # Collect all audio
        audio_chunks = []
        while not self.audio_queue.empty():
            audio_chunks.append(self.audio_queue.get())
        
        audio_bytes = b''.join([chunk.tobytes() for chunk in audio_chunks])
        print(f"✓ Recorded {len(audio_bytes)} bytes")
        return audio_bytes
    
    def send_query(self, audio_bytes):
        """Send to backend - SAME endpoint as frontend!"""
        audio_b64 = base64.b64encode(audio_bytes).decode('ascii')
        
        # EXACT SAME REQUEST AS FRONTEND
        response = requests.post(
            f'{self.api_url}/agent/stream',
            headers={
                'Content-Type': 'application/json',
                'X-Tenant-Id': 'tenant-demo',
            },
            json={
                'session_id': self.session_id,
                'input_type': 'audio',
                'audio': {
                    'audio_b64': audio_b64,
                    'sample_rate_hz': 16000,
                },
                'domain': self.domain,
                'language': self.language,
                'output_audio': True,
                'tts_provider': 'qwen',
                'tts_voice': 'indic-hindi-female',
            },
            stream=True,
        )
        
        # Process SSE stream - SAME as frontend
        print("🔄 Processing...")
        
        transcript = ""
        response_text = ""
        
        for line in response.iter_lines():
            if not line:
                continue
            
            line = line.decode('utf-8')
            
            # Parse SSE
            if line.startswith('event: '):
                event = line[7:]
            elif line.startswith('data: '):
                data = json.loads(line[6:])
                
                if event == 'input':
                    transcript = data.get('transcript', '')
                    print(f"\n📝 You said: {transcript}")
                
                elif event == 'text':
                    # Streaming text response
                    response_text += data
                    print(data, end='', flush=True)
                
                elif event == 'audio':
                    # Audio chunk ready
                    audio_b64 = data['audio_b64']
                    audio_chunk = base64.b64decode(audio_b64)
                    
                    # Play immediately (like frontend)
                    self.play_audio(audio_chunk)
                
                elif event == 'done':
                    print("\n✓ Done")
    
    def play_audio(self, audio_bytes):
        """Play audio chunk"""
        # Parse WAV header if present
        import wave
        import io
        
        try:
            with wave.open(io.BytesIO(audio_bytes), 'rb') as wf:
                audio_data = np.frombuffer(wf.readframes(wf.getnframes()), dtype='int16')
                sd.play(audio_data, wf.getframerate())
                sd.wait()
        except:
            # Raw PCM16
            audio_data = np.frombuffer(audio_bytes, dtype='int16')
            sd.play(audio_data, 16000)
            sd.wait()
    
    def run(self):
        """Main loop - like frontend button press/release"""
        print("="*60)
        print("Voice Toy - Using Frontend Endpoints!")
        print("="*60)
        print(f"Domain: {self.domain}")
        print(f"Language: {self.language}")
        print("="*60)
        
        while True:
            input("\nPress Enter to speak...")
            
            # Start recording
            self.start_recording()
            
            # Wait for user to press Enter again
            input()  # Stop recording
            
            audio_bytes = self.stop_recording()
            
            # Send to backend (same as frontend)
            self.send_query(audio_bytes)

# Run it!
if __name__ == '__main__':
    toy = VoiceToy(
        api_url='https://your-backend.run.app',
        domain='education',
        language='hi-IN',
    )
    toy.run()
```

**This toy uses the EXACT SAME `/agent/stream` endpoint as your frontend!**

---

## Advanced: Auto Voice Detection (Like Frontend)

If your frontend has voice activity detection (VAD), the toy can do the same:

```python
import webrtcvad

class SmartVoiceToy:
    def __init__(self):
        self.vad = webrtcvad.Vad(3)  # Aggressiveness 0-3
        self.api_url = "https://your-backend.run.app"
    
    def auto_detect_and_record(self):
        """Automatically detect voice and record (like frontend)"""
        print("🎤 Listening...")
        
        # Buffer for audio
        audio_buffer = []
        silence_frames = 0
        recording = False
        
        def callback(indata, frames, time, status):
            nonlocal recording, silence_frames
            
            # Check if speech present
            is_speech = self.vad.is_speech(indata.tobytes(), 16000)
            
            if is_speech:
                if not recording:
                    print("🗣️ Speech detected! Recording...")
                    recording = True
                
                audio_buffer.append(indata.copy())
                silence_frames = 0
            
            elif recording:
                # Count silence frames
                silence_frames += 1
                audio_buffer.append(indata.copy())
                
                # Stop if 1 second of silence
                if silence_frames > 16:  # 16 frames = 1 sec at 16kHz
                    print("✓ Speech ended")
                    return  # Stop callback
        
        # Start stream with VAD callback
        with sd.InputStream(samplerate=16000, channels=1, dtype='int16', 
                           callback=callback):
            # Wait for recording to complete
            while recording or silence_frames < 16:
                time.sleep(0.1)
        
        # Combine audio chunks
        audio_bytes = b''.join([chunk.tobytes() for chunk in audio_buffer])
        return audio_bytes
    
    def run(self):
        """Auto voice detection loop"""
        while True:
            # Auto-detect voice (like frontend)
            audio_bytes = self.auto_detect_and_record()
            
            # Send to backend (same endpoint as frontend)
            self.send_to_backend(audio_bytes)
```

---

## WebSocket Mode (Even More Like Frontend!)

Your frontend might use WebSocket (`/agent/ws`). The toy can use it too:

```python
import websocket
import json
import base64
import threading

class WebSocketVoiceToy:
    def __init__(self, api_url, domain="education"):
        self.ws_url = api_url.replace('https://', 'wss://') + '/agent/ws'
        self.domain = domain
        self.ws = None
    
    def connect(self):
        """Connect to WebSocket (same as frontend)"""
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            header={
                'X-Tenant-Id': 'tenant-demo',
            },
            on_message=self.on_message,
            on_open=self.on_open,
        )
        
        # Run in background
        wst = threading.Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()
    
    def on_open(self, ws):
        """Send start message (like frontend)"""
        ws.send(json.dumps({
            'type': 'start',
            'domain': self.domain,
            'language': 'hi-IN',
            'output_audio': True,
            'tts_provider': 'qwen',
            'tts_voice': 'indic-hindi-female',
        }))
        print("✓ Connected to WebSocket")
    
    def on_message(self, ws, message):
        """Handle messages (same as frontend)"""
        data = json.loads(message)
        event = data.get('event')
        
        if event == 'ready':
            print("🎤 Ready for voice input")
        
        elif event == 'input':
            transcript = data['data'].get('transcript', '')
            print(f"\n📝 You said: {transcript}")
        
        elif event == 'text':
            # Streaming text
            print(data['data'], end='', flush=True)
        
        elif event == 'audio':
            # Audio chunk
            audio_b64 = data['data']['audio_b64']
            self.play_audio(base64.b64decode(audio_b64))
        
        elif event == 'done':
            print("\n✓ Done")
    
    def send_audio(self, audio_bytes):
        """Send audio chunk (like frontend sends chunks)"""
        audio_b64 = base64.b64encode(audio_bytes).decode('ascii')
        
        self.ws.send(json.dumps({
            'type': 'audio_chunk',
            'audio_b64': audio_b64,
        }))
    
    def end_turn(self):
        """End recording (like frontend button release)"""
        self.ws.send(json.dumps({'type': 'audio_end'}))
```

---

## Summary: Frontend vs Toy

### They're THE SAME! ✅

| Feature | Frontend | Toy | Endpoint |
|---------|----------|-----|----------|
| Voice input | ✅ Microphone | ✅ Microphone | `/agent/stream` |
| Domain selection | ✅ Dropdown | ✅ Config | `/agent/stream` |
| Language | ✅ User choice | ✅ Device config | `/agent/stream` |
| TTS voice | ✅ User choice | ✅ Device config | `/agent/stream` |
| Audio output | ✅ Browser plays | ✅ Speaker plays | `/agent/stream` |
| Session memory | ✅ session_id | ✅ session_id | `/agent/stream` |
| Streaming | ✅ SSE chunks | ✅ SSE chunks | `/agent/stream` |

**The toy is just a different "frontend"! It's a physical device instead of a web browser, but it uses the EXACT SAME backend API!**

---

## When to Use MQTT Endpoints vs Frontend Endpoints

### Use Frontend Endpoints (`/agent/stream`) When:
- ✅ You want toys to work exactly like frontend
- ✅ You want same features (streaming, session memory, etc.)
- ✅ You want to reuse tested, working code
- ✅ Simple deployment (no extra config needed)

### Use MQTT Endpoints (`/mqtt/*`) When:
- ✅ You need per-device config storage
- ✅ You want simplified API for embedded devices
- ✅ You need device management features
- ✅ You plan to use true MQTT protocol later
- ✅ You want built-in device capabilities (STT/TTS combos)

**For most cases, just use `/agent/stream` - it's simpler!**

---

## Complete Working Example: Toy Using Frontend Endpoint

```python
#!/usr/bin/env python3
"""
Complete voice toy that uses SAME endpoints as frontend
No MQTT needed!
"""

import requests
import base64
import json
import sounddevice as sd
import numpy as np
import wave
import io

API_URL = "https://your-backend.run.app"
DOMAIN = "education"
LANGUAGE = "hi-IN"
TTS_VOICE = "indic-hindi-female"

def record_audio(duration=5):
    """Record audio from microphone"""
    print(f"🎤 Recording for {duration} seconds...")
    audio = sd.rec(
        int(duration * 16000),
        samplerate=16000,
        channels=1,
        dtype='int16',
    )
    sd.wait()
    return audio.tobytes()

def play_audio(audio_bytes):
    """Play audio through speaker"""
    try:
        with wave.open(io.BytesIO(audio_bytes), 'rb') as wf:
            data = np.frombuffer(wf.readframes(wf.getnframes()), dtype='int16')
            sd.play(data, wf.getframerate())
            sd.wait()
    except:
        data = np.frombuffer(audio_bytes, dtype='int16')
        sd.play(data, 16000)
        sd.wait()

def voice_interaction(session_id="session-123"):
    """
    Complete voice interaction using frontend endpoint
    SAME AS FRONTEND!
    """
    # Record audio
    audio_bytes = record_audio(duration=5)
    audio_b64 = base64.b64encode(audio_bytes).decode('ascii')
    
    # Call backend - SAME ENDPOINT AS FRONTEND
    print("🔄 Processing (STT + Chat + TTS)...")
    response = requests.post(
        f'{API_URL}/agent/stream',
        headers={
            'Content-Type': 'application/json',
            'X-Tenant-Id': 'tenant-demo',
        },
        json={
            'session_id': session_id,
            'input_type': 'audio',
            'audio': {
                'audio_b64': audio_b64,
                'sample_rate_hz': 16000,
            },
            'domain': DOMAIN,
            'language': LANGUAGE,
            'output_audio': True,
            'tts_provider': 'qwen',
            'tts_voice': TTS_VOICE,
        },
        stream=True,
    )
    
    # Process SSE stream - SAME AS FRONTEND
    current_event = None
    transcript = ""
    response_text = ""
    
    for line in response.iter_lines():
        if not line:
            continue
        
        line = line.decode('utf-8')
        
        if line.startswith('event: '):
            current_event = line[7:]
        
        elif line.startswith('data: '):
            try:
                data = json.loads(line[6:])
            except:
                continue
            
            if current_event == 'input':
                transcript = data.get('transcript', '')
                print(f"\n📝 You said: {transcript}")
            
            elif current_event == 'text':
                piece = data if isinstance(data, str) else data.get('text', '')
                response_text += piece
                print(piece, end='', flush=True)
            
            elif current_event == 'audio':
                # Play audio chunk immediately
                audio_b64 = data.get('audio_b64', '')
                if audio_b64:
                    print("\n🔊 Playing response...")
                    play_audio(base64.b64decode(audio_b64))
            
            elif current_event == 'done':
                print("\n✓ Done")
    
    return transcript, response_text

# Main loop
if __name__ == '__main__':
    import time
    session_id = f"toy-{int(time.time())}"
    
    print("="*60)
    print("Voice Toy - Using Frontend Endpoints!")
    print("="*60)
    print(f"API: {API_URL}")
    print(f"Domain: {DOMAIN}")
    print(f"Language: {LANGUAGE}")
    print(f"Voice: {TTS_VOICE}")
    print("="*60)
    
    while True:
        input("\nPress Enter to speak...")
        try:
            voice_interaction(session_id)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    print("\nGoodbye!")
```

**Save as `simple_toy.py` and run it! Uses SAME endpoints as your frontend!**

---

## Conclusion

**YES, toys can and SHOULD use the same endpoints as your frontend!**

- `/agent/stream` - For HTTP streaming (like frontend)
- `/agent/ws` - For WebSocket (if frontend uses it)
- `/voice/transcribe` - For STT only
- `/voice/synthesize` - For TTS only

**The MQTT endpoints (`/mqtt/*`) were created as an ALTERNATIVE option with extra features, but they're NOT required. The toys are just another "client" like your web frontend, using the same backend API!**

**Recommendation: Start with `/agent/stream` endpoint (simpler, already tested). Only use `/mqtt/*` if you need device management features.**
