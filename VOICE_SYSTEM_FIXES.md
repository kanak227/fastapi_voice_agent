# Voice System Fixes Summary

## Issue Reported
"When I choose other voice, still I hear the same voice"

## Root Cause Analysis

The voice selection was not working because the Qwen TTS server had a bug in the `_qwen_synthesize()` function:

```python
# BEFORE (BUG):
def _qwen_synthesize(text: str, language: str) -> tuple[np.ndarray, int]:
    speaker = DEFAULT_VOICE_ID  # Always used default voice!
    # ...
```

The function was hardcoded to always use `DEFAULT_VOICE_ID` instead of using the `voice_id` parameter passed from the HTTP request.

## Voice Selection Flow

The voice selection flow works as follows:

1. **Frontend** (`tts-settings.js`): User selects voice → stored in localStorage as `voiceId`
2. **Frontend** (`voice-streaming.js`): Reads settings → passes as `tts_voice` parameter
3. **API Route** (`/api/Voice/agent/route.js`): Receives `tts_voice` → forwards to backend
4. **Backend Router** (`/voice/synthesize`): Receives `voice` parameter → forwards to provider
5. **Backend Provider** (`deepgram_elevenlabs_provider.py`): Receives `voice` → passes to TTS service
6. **TTS Service** (`tts-qwen3/server.py`): **BUG WAS HERE** - ignored the voice parameter!

## Fix Applied

### File: `tts-qwen3/server.py`

**Change 1**: Modified `_qwen_synthesize()` to accept speaker parameter

```python
# AFTER (FIXED):
def _qwen_synthesize(text: str, language: str, speaker: str = None) -> tuple[np.ndarray, int]:
    speaker = speaker or DEFAULT_VOICE_ID  # Use provided speaker or default
    with app.state.qwen_lock:
        _set_seed(SEED)
        wavs, sr = app.state.qwen_model.generate_custom_voice(
            text=text,
            speaker=speaker,  # Now uses the correct speaker!
            language=language,
        )
    # ...
```

**Change 2**: Updated `text_to_speech()` endpoint to pass voice to synthesis

```python
# AFTER (FIXED):
try:
    if engine == "qwen":
        audio, sr = _qwen_synthesize(text, arg, speaker=voice)  # Pass voice!
    else:
        audio, sr = _mms_synthesize(text, arg)
except Exception as exc:
    # ...
```

## Testing

### Automated Tests Created

**File**: `tests/voice_system_test.py`

Comprehensive automated test script that tests:
- ✅ Voice listing API for both ElevenLabs and Qwen
- ✅ Voice listing with language filters
- ✅ TTS synthesis for all 17 supported languages
- ✅ TTS synthesis with different voice selections
- ✅ STT transcription for all languages
- ✅ Complete voice agent endpoint integration
- ✅ Multiple language + domain + provider combinations

**Usage**:
```bash
# Set environment variables
export BACKEND_URL=http://localhost:8000
export FRONTEND_URL=http://localhost:3000
export TENANT_ID=default

# Run tests
python tests/voice_system_test.py
```

### Manual Testing Checklist Created

**File**: `VOICE_TESTING_CHECKLIST.md`

Detailed manual testing checklist covering:
- ✅ Voice selection verification (does voice actually change?)
- ✅ STT testing for all languages and bots
- ✅ TTS response quality testing
- ✅ Pause handling verification
- ✅ Voice streaming functionality
- ✅ Cross-language voice consistency
- ✅ Edge cases and error handling

## Verification Steps

To verify the fix works:

1. **Restart the Qwen TTS server** (the fix is in `tts-qwen3/server.py`)
2. Open any bot dashboard
3. Select "Offline (Qwen)" mode
4. Select "Serena" voice
5. Type: "Hello, this is a test"
6. Listen to the voice (should be female)
7. Select "Ethan" voice
8. Type: "Hello, this is a test"
9. Listen to the voice (should be male and sound different)

**Expected Result**: The voices should sound noticeably different!

## Impact

This fix affects:
- ✅ All 10 bot domains
- ✅ All 17 supported languages
- ✅ Qwen (offline) TTS provider
- ✅ Voice selection in the TTS settings panel

**Note**: ElevenLabs (online) provider was not affected by this bug.

## Related Issues Fixed Previously

1. ✅ Voice input not working in non-religious/education bots
2. ✅ TTS pause issues (exclamation/question marks)
3. ✅ Chinese and Japanese voice support
4. ✅ Voice filtering for different languages

## Deployment

To deploy this fix to production:

```bash
# Commit is already created
git push origin main

# Deploy to GCP Cloud Run
gcloud builds submit --config=deployment/gcp/cloudbuild.yaml --substitutions=SHORT_SHA=$(git rev-parse --short HEAD)
```

The Qwen TTS service will need to be restarted to pick up the changes.

## Files Modified

1. `tts-qwen3/server.py` - Fixed voice selection bug
2. `tests/voice_system_test.py` - New automated test suite
3. `VOICE_TESTING_CHECKLIST.md` - New manual testing checklist
4. `VOICE_SYSTEM_FIXES.md` - This summary document

## Commit

```
commit b34c354
Author: [Your Name]
Date: [Date]

fix: voice selection not working in Qwen TTS + comprehensive test suite

- Fixed bug where Qwen TTS always used default voice instead of selected voice
- Modified _qwen_synthesize() to accept and use speaker parameter
- Updated text_to_speech endpoint to pass resolved voice_id to synthesis
- Added comprehensive automated test script (tests/voice_system_test.py)
- Added detailed manual testing checklist (VOICE_TESTING_CHECKLIST.md)
- Tests cover: voice listing, STT, TTS, voice selection, all languages, all bots
```
