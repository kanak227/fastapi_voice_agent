# Voice System Tests

## Overview

This directory contains automated tests for the voice system (STT and TTS).

## Test Files

- **`voice_system_test.py`** - Comprehensive automated test suite for voice system

## Prerequisites

### Python Dependencies

Install required packages:

```bash
pip install httpx numpy
```

### Running Services

Make sure these services are running:

1. **Backend (FastAPI)**: `http://localhost:8000`
2. **Frontend (Next.js)**: `http://localhost:3000`
3. **Qwen TTS Service**: Should be accessible via backend

## Running Tests

### Basic Usage

```bash
# Run all tests with default settings
python voice_system_test.py
```

### Custom Configuration

Set environment variables to customize test configuration:

```bash
# Windows (CMD)
set BACKEND_URL=http://localhost:8000
set FRONTEND_URL=http://localhost:3000
set TENANT_ID=default
python voice_system_test.py

# Windows (PowerShell)
$env:BACKEND_URL="http://localhost:8000"
$env:FRONTEND_URL="http://localhost:3000"
$env:TENANT_ID="default"
python voice_system_test.py

# Linux/Mac
export BACKEND_URL=http://localhost:8000
export FRONTEND_URL=http://localhost:3000
export TENANT_ID=default
python voice_system_test.py
```

### Testing Against Production

```bash
# Windows (PowerShell)
$env:BACKEND_URL="https://multi-bot-server-t5wdyzp3ta-uc.a.run.app"
$env:FRONTEND_URL="https://chatbot-frontend-t5wdyzp3ta-uc.a.run.app"
$env:TENANT_ID="default"
python voice_system_test.py
```

## Test Suites

The test script runs four test suites:

### 1. Voice Listing Tests
- Tests voice listing API for ElevenLabs and Qwen
- Tests language filtering
- Verifies voice metadata (name, voice_id, locale, gender)

### 2. TTS Synthesis Tests
- Tests TTS for all 17 supported languages
- Tests voice selection with different voices
- Verifies audio generation

### 3. STT Transcription Tests
- Tests STT for all 17 supported languages
- Verifies transcription endpoint
- **Note**: Uses synthetic audio, so transcripts may be empty

### 4. Integration Tests
- Tests complete voice agent flow
- Tests multiple language + domain + provider combinations
- Verifies end-to-end functionality

## Understanding Test Results

### Success Indicators

✅ **Green checkmarks** - Test passed  
❌ **Red X marks** - Test failed  
⚠️ **Yellow warnings** - Test passed with notes

### Expected Behavior

- **Voice Listing**: Should return voices for each provider
- **TTS Synthesis**: Should generate audio bytes
- **STT Transcription**: Should return transcript (may be empty for synthetic audio)
- **Integration**: Should complete full voice agent flow

### Known Limitations

1. **Synthetic Audio**: The test uses generated sine wave audio, not real speech
   - STT transcripts will likely be empty or inaccurate
   - This is expected and doesn't indicate a bug
   
2. **Audio Quality**: Tests verify that audio is generated but cannot verify:
   - Voice quality
   - Pronunciation accuracy
   - Natural pauses
   - Voice differences between selections
   
3. **Manual Testing Required**: For audio quality verification, use the manual testing checklist:
   - `../VOICE_TESTING_CHECKLIST.md`

## Interpreting Results

### All Tests Pass
✅ API endpoints are working correctly  
✅ Voice listing is functional  
✅ TTS and STT services are responding  
✅ Integration flow is complete  

**Next Step**: Run manual tests to verify audio quality

### Some Tests Fail

Check the error messages:

- **Connection errors**: Services may not be running
- **401/403 errors**: Authentication issues
- **500 errors**: Backend service errors
- **Timeout errors**: Services may be slow or overloaded

### Example Output

```
================================================================================
                      Voice System Comprehensive Test Suite                      
================================================================================

ℹ Backend URL: http://localhost:8000
ℹ Frontend URL: http://localhost:3000
ℹ Tenant ID: default

================================================================================
                            Voice Listing Tests                            
================================================================================

ℹ Testing elevenlabs voice listing...
✓ elevenlabs: Found 12 voices (no filter)
✓ elevenlabs (English): Found 12 voices
✓ elevenlabs (Hindi): Found 3 voices
...

Voice Listing Results: 15 passed, 0 failed

================================================================================
                            TTS Synthesis Tests                            
================================================================================

ℹ Testing elevenlabs TTS synthesis...
✓ elevenlabs (English): TTS synthesis successful
✓ elevenlabs (Hindi): TTS synthesis successful
...

TTS Synthesis Results: 34 passed, 0 failed

...
```

## Troubleshooting

### Tests Won't Run

**Error**: `ModuleNotFoundError: No module named 'httpx'`  
**Solution**: Install dependencies: `pip install httpx numpy`

**Error**: `Connection refused`  
**Solution**: Make sure backend and frontend services are running

### All Tests Fail

1. Check if services are running:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:3000
   ```

2. Check environment variables:
   ```bash
   echo $BACKEND_URL
   echo $FRONTEND_URL
   ```

3. Check logs:
   - Backend logs for errors
   - Frontend console for errors

### Specific Test Failures

**Voice Listing Fails**:
- Check if ElevenLabs API key is set
- Check if Qwen TTS service is running

**TTS Synthesis Fails**:
- Check provider configuration
- Check API keys
- Check service logs

**STT Transcription Fails**:
- Check Deepgram API key
- Check audio format compatibility

**Integration Tests Fail**:
- Check all services are running
- Check network connectivity
- Check authentication

## Manual Testing

For comprehensive testing including audio quality verification, use the manual testing checklist:

📋 **[VOICE_TESTING_CHECKLIST.md](../VOICE_TESTING_CHECKLIST.md)**

The manual checklist covers:
- Voice selection verification
- Audio quality assessment
- Pause handling
- Cross-language consistency
- Edge cases

## Contributing

When adding new tests:

1. Follow the existing test structure
2. Use descriptive test names
3. Add appropriate success/failure messages
4. Update this README with new test information

## Support

For issues or questions:
1. Check the main documentation
2. Review test output for error messages
3. Check service logs
4. Consult the manual testing checklist
