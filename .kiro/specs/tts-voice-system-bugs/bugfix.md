# Bugfix Requirements Document

## Introduction

The TTS/voice system has multiple bugs affecting audio playback quality, cross-bot voice support, language coverage, and voice catalog accuracy. These bugs collectively degrade the voice experience: offline TTS has audible gaps between chunks, non-Religious bots fail silently on voice turns due to missing refs and incomplete streaming implementation, certain languages produce silence or errors, the voice list ignores the user's selected language, and the offline voice catalog is too limited. Fixing these issues will deliver a consistent, working voice experience across all bots and languages.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN using the offline Qwen3 TTS provider THEN the system produces audible gaps/pauses between sentence chunks because TTS synthesis is sequential with no pre-buffering of the next chunk while the current one plays

1.2 WHEN using non-streaming mode for voice responses THEN the system truncates the assistant reply to 280 characters and at most 2 sentences via `clampVoiceAssistantReply()`, which can cut mid-thought and produce unclear spoken output

1.3 WHEN using the Eduthum bot (or any non-Religious bot) with voice THEN the system fails silently because `handleVoiceTurn` references `voiceAbortRef.current` and `currentAudioRef.current` which are never declared, and does not pass `abortSignal`, `history`, or `onTextToken` to `streamRecordedVoiceTurn`

1.4 WHEN selecting Urdu (`ur`) language with the offline Qwen3/MMS TTS provider THEN the system produces silence or errors because MMS requires the `uroman` package for romanization and the fallback returns untokenizable original text

1.5 WHEN selecting Hinglish (`hi-Latn`) language with the offline TTS provider THEN the system produces broken audio because `_latn_to_devanagari()` requires the `indic-transliteration` package and without it passes Latin text directly to MMS Hindi which expects Devanagari script

1.6 WHEN selecting Urdu (`ur`) language with the ElevenLabs provider THEN the system may fail because `_ELEVENLABS_LANG_MAP` does not include `ur`, causing the language code to fall through to a raw split that may not be supported

1.7 WHEN opening the voice selection panel THEN the system shows all available voices regardless of the currently selected language, including voices that do not support the user's chosen language

1.8 WHEN using the offline TTS provider THEN the system only shows 2 hardcoded voices (Serena, Ethan) with no language metadata, and MMS-TTS languages are single-speaker with no voice choice communicated to the user

1.9 WHEN the Eduthum bot's `handleVoiceTurn` encounters a speaking phase THEN the system cannot stop playback because `stopVoicePlayback()` is not implemented and the voice orb does not handle the speaking/processing state for abort

### Expected Behavior (Correct)

2.1 WHEN using the offline Qwen3 TTS provider THEN the system SHALL pre-buffer the next TTS chunk synthesis concurrently while the current chunk is playing, so that audio playback is continuous without audible gaps

2.2 WHEN using non-streaming mode for voice responses THEN the system SHALL either increase the character limit to accommodate full natural responses or use streaming mode by default so that responses are not truncated mid-sentence

2.3 WHEN using the Eduthum bot (or any non-Religious bot) with voice THEN the system SHALL declare `voiceAbortRef`, `currentAudioRef`, and `voiceAbortControllerRef` refs, pass `abortSignal`, `history`, and `onTextToken` to `streamRecordedVoiceTurn`, and implement `stopVoicePlayback()` matching the Religious bot's working implementation

2.4 WHEN selecting Urdu (`ur`) language with the offline Qwen3/MMS TTS provider THEN the system SHALL ensure the `uroman` package is installed and available, or provide a clear error message if romanization cannot be performed

2.5 WHEN selecting Hinglish (`hi-Latn`) language with the offline TTS provider THEN the system SHALL ensure the `indic-transliteration` package is installed and available, or provide a clear error message if transliteration cannot be performed

2.6 WHEN selecting Urdu (`ur`) language with the ElevenLabs provider THEN the system SHALL include `ur` in `_ELEVENLABS_LANG_MAP` so the language code is correctly passed to the ElevenLabs API

2.7 WHEN opening the voice selection panel THEN the system SHALL filter the displayed voices based on the currently selected language, showing only voices that support that language

2.8 WHEN using the offline TTS provider THEN the system SHALL expand the voice catalog with additional voices where supported, and clearly indicate in the UI when a language uses single-speaker MMS (no voice choice available)

2.9 WHEN the Eduthum bot's voice is in speaking or processing phase THEN the system SHALL allow the user to stop playback via the voice orb, aborting the SSE stream and stopping the current audio element

### Unchanged Behavior (Regression Prevention)

3.1 WHEN using the ElevenLabs (online) TTS provider with English THEN the system SHALL CONTINUE TO synthesize and play audio per-sentence with low latency as it does today

3.2 WHEN using the Religious bot with voice THEN the system SHALL CONTINUE TO handle the full streaming voice pipeline including abort, text streaming, and audio playback without regression

3.3 WHEN using text chat (non-voice) on any bot THEN the system SHALL CONTINUE TO display full untruncated responses in the chat bubble

3.4 WHEN selecting English, French, German, Spanish, or other Qwen-supported languages THEN the system SHALL CONTINUE TO route to the Qwen3 engine and produce correct audio

3.5 WHEN using the TTS settings panel to switch between Online/Offline providers THEN the system SHALL CONTINUE TO persist the selection in localStorage and apply it to subsequent voice requests

3.6 WHEN the voice orb is pressed during idle state on any bot THEN the system SHALL CONTINUE TO start microphone listening and capture audio for the voice turn

3.7 WHEN streaming mode is used for voice responses THEN the system SHALL CONTINUE TO emit SSE events (input, text, audio, final_text, done) in the correct order
