# TTS Voice System Bugs — Bugfix Design

## Overview

The TTS/voice system has nine interrelated bugs spanning audio playback quality, cross-bot voice support, language coverage, and voice catalog accuracy. The fix strategy addresses each bug at its root: (1) add concurrent pre-buffering in the TTS streaming worker to eliminate gaps, (2) increase or remove the 280-char clamp for non-streaming replies, (3) add missing refs and abort support to the Eduthum bot page, (4–5) ensure `uroman` and `indic-transliteration` packages are installed and importable in the offline TTS container, (6) add `ur` to the ElevenLabs language map, (7–8) add language filtering to the voice list endpoint and expand the offline voice catalog with language metadata, and (9) implement `stopVoicePlayback` in the Eduthum bot.

## Glossary

- **Bug_Condition (C)**: The set of conditions under which any of the nine bugs manifest — offline TTS gaps, truncated replies, missing refs, language failures, unfiltered voice lists, or missing abort support.
- **Property (P)**: The desired correct behavior — gapless audio, full-length replies, working voice on all bots, correct language synthesis, filtered voice lists, and functional playback stop.
- **Preservation**: Existing behaviors that must remain unchanged — ElevenLabs English streaming, Religious bot voice pipeline, text chat responses, Qwen-supported language routing, TTS settings persistence, voice orb idle-start behavior, SSE event ordering.
- **`tts_stream()` generator** (`fastapi_server/app/routers/agent.py`): The async generator that intercepts bot SSE, buffers sentences, synthesizes TTS, and emits audio events.
- **`clampVoiceAssistantReply()`** (`app/api/Voice/agent/route.js`): Function that truncates non-streaming voice replies to 280 chars / 2 sentences.
- **`VOICE_CATALOG`** (`tts-qwen3/server.py`): Hardcoded list of voices exposed by the offline TTS service.
- **`_ELEVENLABS_LANG_MAP`** (`deepgram_elevenlabs_provider.py`): Mapping from BCP-47 codes to ElevenLabs language codes used during synthesis.

## Bug Details

### Bug Condition

The bugs manifest across nine distinct conditions in the TTS/voice pipeline. The system either produces degraded audio, fails silently, or shows incorrect UI state when any of these conditions hold.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type VoiceRequest
  OUTPUT: boolean

  // Bug 1: Offline TTS gaps
  IF input.tts_provider == "qwen" AND input.stream == true
     AND input.response_has_multiple_sentences == true
     RETURN true

  // Bug 2: Non-streaming truncation
  IF input.stream == false AND len(input.assistant_reply) > 280
     RETURN true

  // Bug 3: Eduthum bot missing refs
  IF input.bot == "eduthum" AND input.mode == "voice"
     RETURN true

  // Bug 4: Urdu on MMS
  IF input.language == "ur" AND input.tts_provider == "qwen"
     AND uroman_not_installed()
     RETURN true

  // Bug 5: Hinglish on MMS
  IF input.language == "hi-Latn" AND input.tts_provider == "qwen"
     AND indic_transliteration_not_installed()
     RETURN true

  // Bug 6: Urdu on ElevenLabs
  IF input.language == "ur" AND input.tts_provider == "elevenlabs"
     RETURN true

  // Bug 7: Voice list unfiltered
  IF input.action == "list_voices" AND input.language IS NOT NULL
     RETURN true

  // Bug 8: Offline catalog limited
  IF input.action == "list_voices" AND input.tts_provider == "qwen"
     RETURN true

  // Bug 9: Eduthum can't stop playback
  IF input.bot == "eduthum" AND input.voice_phase IN ["speaking", "processing"]
     AND input.user_action == "stop"
     RETURN true

  RETURN false
END FUNCTION
```

### Examples

- **Bug 1**: User asks a 3-sentence question in English with offline TTS → hears 0.5–2s silence between each sentence clip while the next one synthesizes.
- **Bug 2**: User asks "Explain photosynthesis" in non-streaming mode → gets "Photosynthesis is the process by which plants convert sunlight into energy. It occurs in..." (truncated at 280 chars with "...").
- **Bug 3**: User presses voice orb on Eduthum → `ReferenceError: voiceAbortRef is not defined` crashes the voice turn silently.
- **Bug 4**: User selects Urdu and speaks → MMS tokenizer receives un-romanized Urdu script → produces silence or garbled audio.
- **Bug 5**: User selects Hinglish and types "namaste kaise ho" → `_latn_to_devanagari()` fails silently, passes Latin to MMS Hindi → broken audio.
- **Bug 6**: User selects Urdu with ElevenLabs → language code falls through to raw split producing "ur" which may not map correctly.
- **Bug 7**: User selects Hindi language, opens voice panel → sees all 30+ ElevenLabs voices including English-only ones.
- **Bug 8**: User selects offline provider → sees only "Serena" and "Ethan" with no indication of language support.
- **Bug 9**: User presses voice orb during Eduthum speaking phase → nothing happens, audio continues playing.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- ElevenLabs English streaming must continue to synthesize per-sentence with low latency
- Religious bot voice pipeline (abort, text streaming, audio playback) must work without regression
- Text chat (non-voice) on all bots must display full untruncated responses
- English, French, German, Spanish, and other Qwen-supported languages must continue routing to Qwen3 engine
- TTS settings panel must continue persisting provider/voice selection in localStorage
- Voice orb idle-state press must continue starting microphone listening
- SSE event ordering (input → text → audio → final_text → done) must remain correct

**Scope:**
All inputs that do NOT involve the nine bug conditions should be completely unaffected by this fix. This includes:
- Text-only chat interactions on any bot
- Voice interactions on the Religious bot (already working)
- ElevenLabs synthesis for languages already in the lang map
- Voice list requests without a language filter parameter (backward compatible)
- Offline TTS for single-sentence responses (no gap possible)

## Hypothesized Root Cause

Based on the bug analysis, the root causes are:

1. **Sequential TTS synthesis (Bug 1)**: The `tts_worker()` in `agent.py` processes one sentence at a time. While the client plays chunk N, chunk N+1 hasn't started synthesizing yet. Qwen3 takes 5–8s per sentence on a T4, creating audible gaps.

2. **Hardcoded 280-char clamp (Bug 2)**: `clampVoiceAssistantReply(text, maxChars = 280)` in the Next.js voice agent route was designed for short spoken answers but is too aggressive for educational/informational responses.

3. **Missing React refs and props (Bug 3)**: The Eduthum `page.js` was copied from an earlier version of the Religious bot before abort support was added. It references `voiceAbortRef.current` and `currentAudioRef.current` without declaring them, and doesn't pass `abortSignal`, `history`, or `onTextToken` to `streamRecordedVoiceTurn`.

4. **Missing Python packages (Bugs 4–5)**: The `uroman` and `indic-transliteration` packages are listed in `requirements.txt` but may not be installed in the Docker image if the build cache is stale, or the `_romanize()` / `_latn_to_devanagari()` functions silently fall back to the original text when import fails.

5. **Missing language map entry (Bug 6)**: `_ELEVENLABS_LANG_MAP` in `deepgram_elevenlabs_provider.py` does not include `"ur": "ur"`, so Urdu falls through to `lang_code.split("-")[0]` which produces `"ur"` — this happens to work but is fragile and undocumented.

6. **No language filtering in voice list (Bug 7)**: The `/voice/voices` endpoint and the Next.js proxy don't accept or pass a `language` parameter. The TTS settings panel fetches all voices without filtering.

7. **Minimal voice catalog (Bug 8)**: `VOICE_CATALOG` in `tts-qwen3/server.py` only has 2 entries with no `language` metadata. MMS languages are single-speaker but this isn't communicated.

8. **Missing `stopVoicePlayback` (Bug 9)**: The Eduthum bot's `handleVoiceOrbPress` doesn't handle the speaking/processing state and has no `stopVoicePlayback` function.

## Correctness Properties

Property 1: Bug Condition - Concurrent Pre-Buffering Eliminates Gaps

_For any_ voice streaming request where `tts_provider == "qwen"` and the response contains multiple sentences, the fixed `tts_worker()` SHALL begin synthesizing the next sentence concurrently while the current audio chunk is being transmitted to the client, reducing inter-chunk latency to near zero.

**Validates: Requirements 2.1**

Property 2: Bug Condition - Non-Streaming Replies Not Truncated

_For any_ non-streaming voice request where the assistant reply exceeds 280 characters, the fixed system SHALL either use streaming mode by default or increase the character limit to 2000, ensuring the full natural response is spoken.

**Validates: Requirements 2.2**

Property 3: Bug Condition - Eduthum Bot Voice Pipeline Complete

_For any_ voice turn on the Eduthum bot, the fixed page SHALL declare all required refs (`voiceAbortRef`, `currentAudioRef`, `voiceAbortControllerRef`), pass `abortSignal`, `history`, and `onTextToken` to `streamRecordedVoiceTurn`, and implement `stopVoicePlayback()` matching the Religious bot's implementation.

**Validates: Requirements 2.3, 2.9**

Property 4: Bug Condition - Urdu and Hinglish Synthesis Succeeds

_For any_ synthesis request where `language == "ur"` or `language == "hi-Latn"` on the offline TTS provider, the fixed system SHALL successfully romanize (Urdu) or transliterate (Hinglish) the input text before passing it to MMS, producing audible correct audio.

**Validates: Requirements 2.4, 2.5**

Property 5: Bug Condition - Urdu in ElevenLabs Language Map

_For any_ synthesis request where `language == "ur"` on the ElevenLabs provider, the fixed `_ELEVENLABS_LANG_MAP` SHALL include `"ur": "ur"` so the language code is explicitly mapped rather than relying on fallback string splitting.

**Validates: Requirements 2.6**

Property 6: Bug Condition - Voice List Filtered by Language

_For any_ voice list request that includes a `language` parameter, the fixed system SHALL return only voices that support the specified language, filtering out voices for other languages.

**Validates: Requirements 2.7, 2.8**

Property 7: Preservation - Existing Voice Pipeline Unchanged

_For any_ input where none of the nine bug conditions hold (ElevenLabs English streaming, Religious bot voice, text chat, Qwen-supported languages, TTS settings persistence, voice orb idle-start, SSE event ordering), the fixed system SHALL produce exactly the same behavior as the original system.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `fastapi_server/app/routers/agent.py`

**Function**: `tts_stream()` → `tts_worker()`

**Specific Changes**:
1. **Concurrent pre-buffering**: Modify `tts_worker()` to use a lookahead pattern — maintain a queue of 2 pending synthesis tasks so that while chunk N plays, chunk N+1 is already synthesizing. Use `asyncio.ensure_future()` to start the next synthesis immediately after queuing the current one.
2. **Pipeline parallelism**: Instead of `await tts_queue.get()` → synthesize → `await audio_queue.put()` sequentially, start the next `tts_queue.get()` before the current synthesis completes.

---

**File**: `tekurious-chatbot-main/tekurious-chatbot-ui/app/api/Voice/agent/route.js`

**Function**: `clampVoiceAssistantReply()` and non-streaming path

**Specific Changes**:
1. **Increase clamp limit**: Change `maxChars = 280` to `maxChars = 2000` for the non-streaming fallback path.
2. **Default to streaming**: Change the non-streaming path to default `stream: true` when the client doesn't explicitly request non-streaming, so the full response is spoken via SSE audio events.

---

**File**: `tekurious-chatbot-main/tekurious-chatbot-ui/app/dashboard/Eduthum/page.js`

**Function**: Component body (refs and `handleVoiceTurn`)

**Specific Changes**:
1. **Add missing refs**: Declare `voiceAbortRef`, `currentAudioRef`, and `voiceAbortControllerRef` using `useRef`.
2. **Implement `stopVoicePlayback()`**: Copy the implementation from the Religious bot — abort the SSE stream, pause current audio, reset phase.
3. **Pass missing props to `streamRecordedVoiceTurn`**: Add `abortSignal: abortController.signal`, `history: messages.map(...)`, and `onTextToken` callback for real-time text streaming.
4. **Update `handleVoiceOrbPress`**: Handle speaking/processing state by calling `stopVoicePlayback()`.
5. **Add `onTextToken` handler**: Stream text tokens into the bot bubble in real-time (matching Religious bot pattern).

---

**File**: `tts-qwen3/requirements.txt`

**Specific Changes**:
1. **Verify packages present**: Confirm `uroman>=1.3.1` and `indic-transliteration>=2.3.62` are listed (already done).
2. **Dockerfile verification**: Ensure the Docker build installs these packages and doesn't use a stale layer cache.

---

**File**: `tts-qwen3/server.py`

**Function**: `_romanize()`, `_latn_to_devanagari()`, `VOICE_CATALOG`, `list_voices()`

**Specific Changes**:
1. **Fail loudly on missing packages**: Change `_romanize()` and `_latn_to_devanagari()` to log a warning (not silently return original text) when the package is missing, and raise an HTTP 500 with a clear message.
2. **Expand VOICE_CATALOG**: Add language metadata to each voice entry and add MMS single-speaker "voices" per language so the UI can show them.
3. **Add language filtering to `/v1/voices`**: Accept an optional `language` query parameter and filter the catalog.

---

**File**: `fastapi_server/app/providers/deepgram_elevenlabs_provider.py`

**Function**: `synthesize_text()` → `_ELEVENLABS_LANG_MAP`

**Specific Changes**:
1. **Add `"ur": "ur"`** to `_ELEVENLABS_LANG_MAP`.
2. **Add language filtering to `list_voices()`**: Accept an optional `language` parameter and filter voices by their `locale`/`labels.language` metadata from ElevenLabs.

---

**File**: `fastapi_server/app/routers/voice.py`

**Function**: `list_voices()`

**Specific Changes**:
1. **Add `language` query parameter**: Accept optional `language` param and pass it through to the provider's `list_voices()` / `list_voices_qwen()` methods for filtering.

---

**File**: `tekurious-chatbot-main/tekurious-chatbot-ui/app/api/Voice/voices/route.js`

**Function**: `GET` handler

**Specific Changes**:
1. **Pass `language` param**: Read `language` from searchParams and forward it to the FastAPI `/voice/voices` endpoint.

---

**File**: `tekurious-chatbot-main/tekurious-chatbot-ui/components/tts-settings-panel.js`

**Function**: Voice list fetch effect

**Specific Changes**:
1. **Pass language to voices API**: Include the current voice language in the fetch URL so the backend can filter.
2. **Accept language prop or read from global state**: Wire the selected language into the panel.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bugs on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bugs BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Write tests that simulate each bug condition and assert the expected failure mode. Run these tests on the UNFIXED code to observe failures and understand the root cause.

**Test Cases**:
1. **Offline TTS Gap Test**: Send a multi-sentence response through `tts_stream()` with `tts_provider=qwen` and measure inter-chunk timing — expect >3s gaps (will fail on unfixed code)
2. **Non-Streaming Truncation Test**: Send a 500-char assistant reply through the non-streaming path — expect truncation to 280 chars (will fail on unfixed code)
3. **Eduthum Ref Error Test**: Render Eduthum page and trigger `handleVoiceTurn` — expect `ReferenceError` on `voiceAbortRef` (will fail on unfixed code)
4. **Urdu MMS Test**: Call `/v1/text-to-speech/serena` with `language_code=ur` and text "سلام" — expect silence or error if uroman not working (will fail on unfixed code)
5. **Hinglish MMS Test**: Call `/v1/text-to-speech/serena` with `language_code=hi-latn` and text "namaste" — expect broken audio if indic-transliteration not working (will fail on unfixed code)
6. **Urdu ElevenLabs Map Test**: Assert `_ELEVENLABS_LANG_MAP` does not contain key `"ur"` (will fail on unfixed code)
7. **Voice List Filter Test**: Call `/voice/voices?language=hi` — expect all voices returned unfiltered (will fail on unfixed code)

**Expected Counterexamples**:
- Inter-chunk silence of 5–8 seconds for offline TTS multi-sentence responses
- Truncated text ending with "..." at exactly 280 characters
- `ReferenceError: voiceAbortRef is not defined` in Eduthum voice handler
- Empty or garbled audio for Urdu/Hinglish on MMS without proper preprocessing

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := fixedSystem(input)
  ASSERT expectedBehavior(result)
END FOR
```

Specifically:
- Bug 1: Assert inter-chunk gap < 500ms for offline TTS
- Bug 2: Assert non-streaming reply length equals full assistant reply (up to 2000 chars)
- Bug 3: Assert no ReferenceError and voice turn completes successfully on Eduthum
- Bug 4: Assert Urdu synthesis produces non-empty audio bytes
- Bug 5: Assert Hinglish synthesis produces non-empty audio bytes
- Bug 6: Assert `_ELEVENLABS_LANG_MAP["ur"] == "ur"`
- Bug 7: Assert voice list filtered by language returns subset of all voices
- Bug 8: Assert offline voice catalog includes language metadata
- Bug 9: Assert `stopVoicePlayback()` stops audio and resets phase

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT originalSystem(input) = fixedSystem(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for English ElevenLabs streaming, Religious bot voice, text chat, and Qwen-supported languages, then write property-based tests capturing that behavior.

**Test Cases**:
1. **ElevenLabs English Preservation**: Verify English streaming TTS continues to produce audio per-sentence with same latency profile
2. **Religious Bot Preservation**: Verify full voice pipeline (abort, text streaming, audio) works identically after fix
3. **Text Chat Preservation**: Verify text-only chat responses are untruncated and unmodified
4. **Qwen Language Routing Preservation**: Verify English/French/German/Spanish/etc. continue routing to Qwen3 engine
5. **TTS Settings Persistence Preservation**: Verify localStorage read/write for provider/voice selection unchanged
6. **SSE Event Order Preservation**: Verify streaming responses emit events in correct order (input → text → audio → final_text → done)

### Unit Tests

- Test `tts_worker()` concurrent pre-buffering logic with mock synthesizer
- Test `clampVoiceAssistantReply()` with new limit (2000 chars)
- Test `_ELEVENLABS_LANG_MAP` contains all expected language codes including `ur`
- Test `_romanize()` produces romanized output for Urdu text
- Test `_latn_to_devanagari()` produces Devanagari for Latin Hindi input
- Test voice list filtering logic with language parameter
- Test Eduthum page renders without ReferenceError when voice refs are declared

### Property-Based Tests

- Generate random multi-sentence texts and verify offline TTS pre-buffering produces all chunks without timeout gaps
- Generate random assistant replies of varying length and verify non-streaming path doesn't truncate below 2000 chars
- Generate random language codes and verify `_ELEVENLABS_LANG_MAP` lookup never throws, always returns a valid string
- Generate random voice catalogs with language metadata and verify filtering returns correct subset
- Generate random inputs NOT matching any bug condition and verify system output is identical to baseline

### Integration Tests

- End-to-end test: Eduthum bot voice turn from audio capture through TTS playback
- End-to-end test: Urdu voice turn on offline provider from STT through MMS synthesis
- End-to-end test: Voice list fetch with language filter on both ElevenLabs and Qwen providers
- End-to-end test: Stop playback mid-speech on Eduthum bot and verify clean state reset
- End-to-end test: Multi-sentence offline TTS streaming with timing assertions on chunk delivery
