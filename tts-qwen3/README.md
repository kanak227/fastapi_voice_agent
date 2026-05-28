# Qwen3 TTS Service (ElevenLabs-compatible)

A drop-in replacement for ElevenLabs that runs Qwen3-TTS (0.6B custom-voice)
on an NVIDIA T4 GPU VM.

The HTTP shape mirrors ElevenLabs so the existing FastAPI provider can talk to
this service unchanged. Only the base URL needs to switch.

## Endpoints

| Method | Path | Notes |
|---|---|---|
| `GET` | `/health` | liveness; reports model load status |
| `GET` | `/v1/voices` | returns the voice catalog |
| `POST` | `/v1/text-to-speech/{voice_id}` | synthesizes audio |

### Request body (TTS)

```json
{
  "text": "Hello",
  "model_id": "ignored",
  "language_code": "hi",
  "output_format": "mp3_44100_128",
  "voice_settings": { "stability": 0.5 }
}
```

### Response

- `mp3_*` → `audio/mpeg`
- `wav`   → `audio/wav`
- `pcm_*` → `audio/L16;rate=…` (raw int16 PCM)

## Local run

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python server.py
```

Optional env:

| Var | Default |
|---|---|
| `PORT` | `8000` |
| `QWEN_DEVICE` | `cuda` if available else `cpu` |
| `QWEN_DTYPE` | `float16` on GPU else `float32` |
| `QWEN_DEFAULT_VOICE_ID` | `serena` |
| `QWEN_DEFAULT_LANGUAGE` | `English` |
| `TTS_API_KEY` | optional; if set, requires `xi-api-key` header |

## Deploy on a Compute Engine T4 VM

See `deploy_gpu_vm.sh`. It creates an `n1-standard-4` + 1× T4 VM, installs
Docker + NVIDIA Container Toolkit, builds the image, and starts the service.

After deploy, set in `fastapi_server/.env`:

```
ELEVENLABS_BASE_URL=http://<vm-external-ip>:8000/v1
ELEVENLABS_VOICE_ID=serena
```

If you set `TTS_API_KEY` on the VM, also set `ELEVENLABS_API_KEY` to the same
value so the existing provider sends it.
