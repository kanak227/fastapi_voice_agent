# Implementation Plan

## Overview

Fix nine interrelated bugs in the TTS/voice system spanning audio playback quality (concurrent pre-buffering), cross-bot voice support (Eduthum missing refs/abort), language coverage (Urdu/Hinglish failures, ElevenLabs lang map), and voice catalog accuracy (language filtering, expanded catalog). The exploration test (Task 1 in standard workflow) is skipped since bugs were confirmed through code inspection.

## Tasks

- [ ] 1. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Existing Voice Pipeline Behavior
  - **IMPORTANT**: Follow observation-first methodology
  - Observe: ElevenLabs English streaming TTS produces audio per-sentence with low latency on unfixed code
  - Observe: Religious bot voice pipeline (abort, text streaming, audio playback) works correctly on unfixed code
  - Observe: Text chat (non-voice) on all bots displays full untruncated responses on unfixed code
  - Observe: English/French/German/Spanish route to Qwen3 engine correctly on unfixed code
  - Observe: TTS settings panel persists provider/voice selection in localStorage on unfixed code
  - Observe: SSE events emit in correct order (input → text → audio → final_text → done) on unfixed code
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements
  - Verify tests PASS on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [ ] 2. Add concurrent pre-buffering to tts_worker() in agent.py
  - [ ] 2.1 Implement lookahead pre-buffering in `tts_worker()`
    - In `fastapi_server/app/routers/agent.py`, modify the `tts_worker()` inner function inside `tts_stream()`
    - Change from sequential `await tts_queue.get()` → synthesize → `await audio_queue.put()` to a concurrent pipeline
    - Use `asyncio.ensure_future()` to start synthesizing the next sentence immediately after dequeuing the current one
    - Maintain a lookahead of 1-2 pending synthesis tasks so chunk N+1 is synthesizing while chunk N is being transmitted
    - Implementation pattern: dequeue next sentence immediately after starting current synthesis, use `asyncio.gather()` or a pre-fetch task to overlap synthesis with transmission
    - _Bug_Condition: isBugCondition(input) where input.tts_provider == "qwen" AND input.stream == true AND input.response_has_multiple_sentences == true_
    - _Expected_Behavior: Inter-chunk latency reduced to near zero; next chunk ready before current finishes playing_
    - _Preservation: ElevenLabs English streaming must continue to synthesize per-sentence with same latency profile; SSE event ordering unchanged_
    - _Requirements: 2.1, 3.1, 3.7_

- [ ] 3. Increase clampVoiceAssistantReply limit in Voice/agent/route.js
  - [ ] 3.1 Update `clampVoiceAssistantReply()` default maxChars parameter
    - In `tekurious-chatbot-main/tekurious-chatbot-ui/app/api/Voice/agent/route.js`
    - Change `function clampVoiceAssistantReply(text, maxChars = 280)` to `function clampVoiceAssistantReply(text, maxChars = 2000)`
    - This affects the non-streaming fallback path at line ~180: `clampVoiceAssistantReply(mergedReply, 280)` → change to `clampVoiceAssistantReply(mergedReply, 2000)`
    - Also update the sentence split from `.slice(0, 2)` to allow more sentences (remove the 2-sentence cap or increase to 10)
    - _Bug_Condition: isBugCondition(input) where input.stream == false AND len(input.assistant_reply) > 280_
    - _Expected_Behavior: Non-streaming replies up to 2000 chars are spoken in full without truncation_
    - _Preservation: Text chat responses remain untruncated; streaming mode SSE events unchanged_
    - _Requirements: 2.2, 3.3, 3.7_

- [ ] 4. Fix Eduthum page.js - add missing refs, stopVoicePlayback, and streaming props
  - [ ] 4.1 Add missing ref declarations to Eduthum page.js
    - In `tekurious-chatbot-main/tekurious-chatbot-ui/app/dashboard/Eduthum/page.js`
    - Add `const currentAudioRef = useRef(null);` after `voiceTurnActiveRef` declaration
    - Add `const voiceAbortRef = useRef(false);` after `currentAudioRef`
    - Add `const voiceAbortControllerRef = useRef(null);` after `voiceAbortRef`
    - _Requirements: 2.3_
  - [ ] 4.2 Implement `stopVoicePlayback()` function in Eduthum page.js
    - Add the following function (matching Religious bot implementation):
    - ```const stopVoicePlayback = () => { voiceAbortRef.current = true; if (voiceAbortControllerRef.current) { voiceAbortControllerRef.current.abort(); voiceAbortControllerRef.current = null; } if (currentAudioRef.current) { currentAudioRef.current.pause(); currentAudioRef.current.currentTime = 0; currentAudioRef.current = null; } setVoicePhase('idle'); };```
    - Place it after the `playBase64Audio` function
    - _Requirements: 2.9_
  - [ ] 4.3 Update `handleVoiceTurn` to pass `abortSignal`, `history`, and `onTextToken` to `streamRecordedVoiceTurn`
    - Create an `AbortController` at the start of `handleVoiceTurn`: `const abortController = new AbortController(); voiceAbortControllerRef.current = abortController;`
    - Reset abort flag: `voiceAbortRef.current = false;`
    - Add `history: messages.map(m => ({ role: m.sender === 'bot' ? 'assistant' : 'user', content: m.content }))` to the `streamRecordedVoiceTurn` call
    - Add `abortSignal: abortController.signal` to the `streamRecordedVoiceTurn` call
    - Add `onTextToken` callback that streams text tokens into the bot bubble in real-time (matching Religious bot pattern with `botBubbleId` tracking)
    - Update `onAudioChunk` to check `voiceAbortRef.current` before playing
    - Add `voiceAbortControllerRef.current = null;` in the `finally` block
    - _Requirements: 2.3_
  - [ ] 4.4 Update `handleVoiceOrbPress` to handle speaking/processing state
    - Add check at the top of `handleVoiceOrbPress`: `if (voicePhase === 'speaking' || voicePhase === 'processing') { stopVoicePlayback(); return; }`
    - This allows the user to stop playback by pressing the voice orb during speech
    - _Requirements: 2.9_
  - [ ] 4.5 Update `playBase64Audio` to respect abort flag
    - Add `if (voiceAbortRef.current) return;` at the start
    - Set `currentAudioRef.current = audio;` before playing
    - Clear `currentAudioRef.current = null;` in onended/onerror/onpause handlers
    - _Bug_Condition: isBugCondition(input) where input.bot == "eduthum" AND input.mode == "voice"_
    - _Expected_Behavior: No ReferenceError; voice turn completes successfully; abort stops playback_
    - _Preservation: Religious bot voice pipeline unchanged; text chat on Eduthum unchanged_
    - _Requirements: 2.3, 2.9, 3.2, 3.3_

- [ ] 5. Add uroman and indic-transliteration to tts-qwen3 and make failures loud
  - [ ] 5.1 Verify packages in requirements.txt
    - Confirm `uroman>=1.3.1` and `indic-transliteration>=2.3.62` are present in `tts-qwen3/requirements.txt` (already confirmed present)
    - No change needed to requirements.txt itself
    - _Requirements: 2.4, 2.5_
  - [ ] 5.2 Make `_romanize()` fail loudly when uroman is not installed
    - In `tts-qwen3/server.py`, modify `_romanize()` function
    - Change the `except Exception: inst = False` block to log a critical warning: `logger.critical("uroman package not installed — Urdu/script-based TTS will fail")`
    - When `inst is False` and the function is called, instead of returning original text, raise `HTTPException(status_code=500, detail="uroman package required for this language but not installed")`
    - _Requirements: 2.4_
  - [ ] 5.3 Make `_latn_to_devanagari()` fail loudly when indic-transliteration is not installed
    - In `tts-qwen3/server.py`, modify `_latn_to_devanagari()` function
    - Change the `except Exception: return text` to log a critical warning and raise: `logger.critical("indic-transliteration package not installed — Hinglish TTS will fail"); raise HTTPException(status_code=500, detail="indic-transliteration package required for Hinglish but not installed")`
    - _Bug_Condition: isBugCondition(input) where (input.language == "ur" AND uroman_not_installed()) OR (input.language == "hi-Latn" AND indic_transliteration_not_installed())_
    - _Expected_Behavior: Clear HTTP 500 error with actionable message instead of silent failure producing garbled audio_
    - _Preservation: English/French/German/Spanish/other Qwen-supported languages continue routing to Qwen3 engine unchanged_
    - _Requirements: 2.4, 2.5, 3.4_

- [ ] 6. Add "ur": "ur" to _ELEVENLABS_LANG_MAP in deepgram_elevenlabs_provider.py
  - [ ] 6.1 Add Urdu entry to `_ELEVENLABS_LANG_MAP`
    - In `fastapi_server/app/providers/deepgram_elevenlabs_provider.py`, inside `synthesize_text()` method
    - Add `"ur": "ur",` to the `_ELEVENLABS_LANG_MAP` dictionary (after the `"pa": "pa"` entry)
    - _Bug_Condition: isBugCondition(input) where input.language == "ur" AND input.tts_provider == "elevenlabs"_
    - _Expected_Behavior: `_ELEVENLABS_LANG_MAP["ur"]` returns "ur" explicitly; no fallback to string splitting_
    - _Preservation: All other language mappings unchanged; ElevenLabs English streaming unaffected_
    - _Requirements: 2.6, 3.1_

- [ ] 7. Add language filtering to voice list endpoint (voice.py, voices/route.js, tts-settings-panel.js)
  - [ ] 7.1 Add `language` query parameter to FastAPI `/voice/voices` endpoint
    - In `fastapi_server/app/routers/voice.py`, update `list_voices()` function signature
    - Add parameter: `language: str | None = None`
    - Pass `language` to `provider.list_voices()` and `provider.list_voices_qwen()` calls
    - After getting voices list, filter: if `language` is provided, only return voices whose `locale` matches the language base code (e.g., `language="hi"` matches voices with locale containing "hi" or "hindi")
    - _Requirements: 2.7_
  - [ ] 7.2 Update `list_voices()` in `deepgram_elevenlabs_provider.py` to accept language filter
    - Add optional `language: str | None = None` parameter to `list_voices()` method
    - If `language` is provided, filter the returned voices by checking the voice's `locale`/`labels.language` metadata from ElevenLabs against the requested language
    - For ElevenLabs voices, check `labels.accent` or `labels.language` fields
    - _Requirements: 2.7_
  - [ ] 7.3 Update Next.js voices proxy route to pass `language` parameter
    - In `tekurious-chatbot-main/tekurious-chatbot-ui/app/api/Voice/voices/route.js`
    - Read `language` from `searchParams`: `const language = searchParams.get("language") || "";`
    - Append to upstream URL: `${baseUrl}/voice/voices?tts_provider=${encodeURIComponent(ttsProvider)}${language ? `&language=${encodeURIComponent(language)}` : ""}`
    - _Requirements: 2.7_
  - [ ] 7.4 Update `tts-settings-panel.js` to pass language when fetching voices
    - In `tekurious-chatbot-main/tekurious-chatbot-ui/components/tts-settings-panel.js`
    - Accept a `language` prop or read from a shared state/context (e.g., import from `@/lib/tts-settings` or accept as prop)
    - Update the fetch URL in the `useEffect` to include language: `` `/api/Voice/voices?tts_provider=${encodeURIComponent(provider)}${language ? `&language=${encodeURIComponent(language)}` : ""}` ``
    - Add `language` to the `useEffect` dependency array so voices re-fetch when language changes
    - _Bug_Condition: isBugCondition(input) where input.action == "list_voices" AND input.language IS NOT NULL_
    - _Expected_Behavior: Voice list filtered by language; only voices supporting the selected language are shown_
    - _Preservation: Voice list requests without language parameter return all voices (backward compatible); TTS settings persistence unchanged_
    - _Requirements: 2.7, 3.5_

- [ ] 8. Expand VOICE_CATALOG in tts-qwen3/server.py with language metadata and add language filter
  - [ ] 8.1 Expand `VOICE_CATALOG` with language metadata
    - In `tts-qwen3/server.py`, update the `VOICE_CATALOG` list
    - Add `"languages"` field to existing entries: `{"voice_id": "serena", "name": "Serena", "labels": {"gender": "female", "accent": "neutral"}, "languages": ["en", "fr", "de", "es", "it", "pt", "ru", "ja", "ko", "zh"]}`
    - Same for Ethan entry
    - Add MMS single-speaker voice entries per language so the UI can show them:
      - `{"voice_id": "mms-hindi", "name": "Hindi (MMS)", "labels": {"gender": "neutral", "accent": "hindi"}, "languages": ["hi"]}`
      - `{"voice_id": "mms-tamil", "name": "Tamil (MMS)", "labels": {"gender": "neutral", "accent": "tamil"}, "languages": ["ta"]}`
      - `{"voice_id": "mms-telugu", "name": "Telugu (MMS)", "labels": {"gender": "neutral", "accent": "telugu"}, "languages": ["te"]}`
      - `{"voice_id": "mms-marathi", "name": "Marathi (MMS)", "labels": {"gender": "neutral", "accent": "marathi"}, "languages": ["mr"]}`
      - `{"voice_id": "mms-bengali", "name": "Bengali (MMS)", "labels": {"gender": "neutral", "accent": "bengali"}, "languages": ["bn"]}`
      - `{"voice_id": "mms-gujarati", "name": "Gujarati (MMS)", "labels": {"gender": "neutral", "accent": "gujarati"}, "languages": ["gu"]}`
      - `{"voice_id": "mms-kannada", "name": "Kannada (MMS)", "labels": {"gender": "neutral", "accent": "kannada"}, "languages": ["kn"]}`
      - `{"voice_id": "mms-malayalam", "name": "Malayalam (MMS)", "labels": {"gender": "neutral", "accent": "malayalam"}, "languages": ["ml"]}`
      - `{"voice_id": "mms-punjabi", "name": "Punjabi (MMS)", "labels": {"gender": "neutral", "accent": "punjabi"}, "languages": ["pa"]}`
      - `{"voice_id": "mms-urdu", "name": "Urdu (MMS)", "labels": {"gender": "neutral", "accent": "urdu"}, "languages": ["ur"]}`
      - `{"voice_id": "mms-arabic", "name": "Arabic (MMS)", "labels": {"gender": "neutral", "accent": "arabic"}, "languages": ["ar"]}`
    - _Requirements: 2.8_
  - [ ] 8.2 Add language filtering to `/v1/voices` endpoint
    - In `tts-qwen3/server.py`, update `list_voices()` route function
    - Add `language: str | None = None` as a query parameter (use `from fastapi import Query`)
    - If `language` is provided, filter `VOICE_CATALOG` to only return voices whose `"languages"` list contains the language base code (e.g., `language.split("-")[0].lower()`)
    - If no `language` param, return all voices (backward compatible)
    - _Bug_Condition: isBugCondition(input) where input.action == "list_voices" AND input.tts_provider == "qwen"_
    - _Expected_Behavior: Offline voice catalog includes language metadata; filtered by language when requested_
    - _Preservation: Voice list requests without language parameter return all voices (backward compatible)_
    - _Requirements: 2.8, 3.5_

- [ ] 9. Verify bug condition tests now pass
  - **Property 1: Expected Behavior** - All Nine Bugs Fixed
  - **IMPORTANT**: Re-run verification against all bug conditions after implementation
  - Verify: Offline TTS multi-sentence responses have no audible gaps (concurrent pre-buffering active)
  - Verify: Non-streaming replies up to 2000 chars are not truncated
  - Verify: Eduthum bot voice turn completes without ReferenceError
  - Verify: Urdu on MMS produces clear error if uroman missing, or correct audio if installed
  - Verify: Hinglish on MMS produces clear error if indic-transliteration missing, or correct audio if installed
  - Verify: `_ELEVENLABS_LANG_MAP["ur"] == "ur"` is explicitly mapped
  - Verify: Voice list with language parameter returns filtered subset
  - Verify: Offline voice catalog has language metadata and filters correctly
  - Verify: Eduthum bot `stopVoicePlayback()` stops audio and resets phase
  - **EXPECTED OUTCOME**: All verifications PASS (confirms bugs are fixed)
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9_

- [ ] 10. Verify preservation tests still pass
  - **Property 2: Preservation** - Existing Voice Pipeline Unchanged
  - **IMPORTANT**: Re-run the SAME tests from task 1 - do NOT write new tests
  - Run preservation property tests from step 1
  - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
  - Confirm ElevenLabs English streaming unchanged
  - Confirm Religious bot voice pipeline unchanged
  - Confirm text chat responses untruncated
  - Confirm Qwen-supported language routing unchanged
  - Confirm TTS settings persistence unchanged
  - Confirm SSE event ordering unchanged
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [ ] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Task Dependency Graph

```json
{
  "waves": [
    [1],
    [2, 3, 4, 5, 6, 7, 8],
    [9],
    [10],
    [11]
  ]
}
```

Tasks 2–8 can be implemented in parallel after task 1 completes. Tasks 9–11 must run sequentially after all implementation tasks.

## Notes

- Task 1 (exploration test) from the standard bugfix workflow is skipped since bugs were confirmed through code inspection.
- The Eduthum fix (task 4) is the most complex single task, involving 5 sub-tasks across refs, functions, and prop passing.
- Tasks 7 and 8 are related (both add language filtering) but target different layers (FastAPI/Next.js proxy vs. offline TTS service).
- The `requirements.txt` already has the needed packages (task 5.1 is verification only); the real fix is making failures loud instead of silent.
