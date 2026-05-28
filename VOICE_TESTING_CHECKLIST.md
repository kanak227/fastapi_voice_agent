# Voice System Manual Testing Checklist

This checklist helps you manually test the voice system across all languages, voices, and bots to ensure everything works correctly.

## Prerequisites

- [ ] Backend server is running
- [ ] Frontend is accessible
- [ ] Microphone is connected and working
- [ ] Speakers/headphones are connected and working
- [ ] Browser has microphone permissions enabled

## Test Environment

- **Frontend URL**: _______________________
- **Test Date**: _______________________
- **Tester Name**: _______________________

---

## Part 1: Voice Selection Test

**Goal**: Verify that selecting different voices actually changes the voice you hear.

### Test Procedure

1. Open any bot dashboard (e.g., Education bot)
2. Click on the voice settings panel (shows "Online" or "Offline")
3. Select **Online (ElevenLabs)** mode
4. Note the current voice name
5. Type a test message: "Hello, this is a voice test"
6. Click the speaker icon to hear the response
7. **Listen carefully** and note the voice characteristics (pitch, gender, accent)
8. Select a **different voice** from the dropdown
9. Type the **same message** again: "Hello, this is a voice test"
10. Click the speaker icon to hear the response
11. **Compare**: Does the voice sound different from step 7?

### Expected Result

✅ **PASS**: The voice sounds noticeably different (different pitch, gender, or accent)  
❌ **FAIL**: The voice sounds exactly the same

### Test Results

| Voice 1 | Voice 2 | Sounds Different? | Notes |
|---------|---------|-------------------|-------|
| _______ | _______ | ☐ Yes ☐ No | _____ |
| _______ | _______ | ☐ Yes ☐ No | _____ |
| _______ | _______ | ☐ Yes ☐ No | _____ |

---

## Part 2: Speech-to-Text (STT) Test

**Goal**: Verify that voice input works correctly for each language in each bot.

### Languages to Test

- [ ] English (en-US)
- [ ] Hindi (hi)
- [ ] Hinglish (hi-Latn)
- [ ] Tamil (ta)
- [ ] Telugu (te)
- [ ] Marathi (mr)
- [ ] Bengali (bn)
- [ ] Gujarati (gu)
- [ ] Kannada (kn)
- [ ] Malayalam (ml)
- [ ] Punjabi (pa)
- [ ] French (fr)
- [ ] German (de)
- [ ] Spanish (es)
- [ ] Arabic (ar)
- [ ] Chinese (zh)
- [ ] Japanese (ja)

### Bots to Test

- [ ] Eduthum (Education)
- [ ] Darshan AI (Religious)
- [ ] Digital Literacy
- [ ] Design Thinking
- [ ] Well-being
- [ ] Sustainability
- [ ] Global Citizenship
- [ ] Entrepreneurship
- [ ] Emotional Intelligence
- [ ] Financial Literacy

### Test Procedure (for each language + bot combination)

1. Open the bot dashboard
2. Select the language from the language dropdown
3. Click the microphone icon
4. Speak a test phrase clearly (see test phrases below)
5. Wait for transcription to appear
6. Check if the transcription is accurate

### Test Phrases by Language

| Language | Test Phrase |
|----------|-------------|
| English | "Hello, how are you today?" |
| Hindi | "नमस्ते, आप कैसे हैं?" |
| Hinglish | "Namaste, aap kaise hain?" |
| Tamil | "வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்?" |
| Telugu | "నమస్కారం, మీరు ఎలా ఉన్నారు?" |
| Marathi | "नमस्कार, तुम्ही कसे आहात?" |
| Bengali | "নমস্কার, আপনি কেমন আছেন?" |
| Gujarati | "નમસ્તે, તમે કેમ છો?" |
| Kannada | "ನಮಸ್ಕಾರ, ನೀವು ಹೇಗಿದ್ದೀರಿ?" |
| Malayalam | "നമസ്കാരം, നിങ്ങൾ എങ്ങനെയുണ്ട്?" |
| Punjabi | "ਸਤ ਸ੍ਰੀ ਅਕਾਲ, ਤੁਸੀਂ ਕਿਵੇਂ ਹੋ?" |
| French | "Bonjour, comment allez-vous?" |
| German | "Hallo, wie geht es dir?" |
| Spanish | "Hola, ¿cómo estás?" |
| Arabic | "مرحبا، كيف حالك؟" |
| Chinese | "你好，你好吗？" |
| Japanese | "こんにちは、お元気ですか？" |

### STT Test Results Template

| Bot | Language | Transcription Appeared? | Accurate? | Notes |
|-----|----------|------------------------|-----------|-------|
| Education | English | ☐ Yes ☐ No | ☐ Yes ☐ No | _____ |
| Education | Hindi | ☐ Yes ☐ No | ☐ Yes ☐ No | _____ |
| Religious | English | ☐ Yes ☐ No | ☐ Yes ☐ No | _____ |
| ... | ... | ... | ... | ... |

---

## Part 3: Text-to-Speech (TTS) Response Test

**Goal**: Verify that voice responses are generated correctly for each language and voice.

### Test Procedure (for each language + provider + voice combination)

1. Open any bot dashboard
2. Select the language
3. Select the TTS provider (Online/Offline)
4. Select a specific voice
5. Type or speak a question
6. Wait for the response
7. Check if audio plays automatically
8. Listen to the audio quality

### Quality Checks

For each response, check:

- [ ] Audio plays without errors
- [ ] Voice is clear and understandable
- [ ] Pronunciation is correct
- [ ] Pauses are natural (not too long or too short)
- [ ] Punctuation is respected (questions sound like questions)
- [ ] No robotic or choppy sound
- [ ] Volume is consistent

### TTS Test Results Template

| Provider | Voice | Language | Audio Plays? | Quality (1-5) | Issues |
|----------|-------|----------|--------------|---------------|--------|
| ElevenLabs | _____ | English | ☐ Yes ☐ No | ☐1 ☐2 ☐3 ☐4 ☐5 | _____ |
| ElevenLabs | _____ | Hindi | ☐ Yes ☐ No | ☐1 ☐2 ☐3 ☐4 ☐5 | _____ |
| Qwen | Serena | English | ☐ Yes ☐ No | ☐1 ☐2 ☐3 ☐4 ☐5 | _____ |
| Qwen | Ethan | English | ☐ Yes ☐ No | ☐1 ☐2 ☐3 ☐4 ☐5 | _____ |
| ... | ... | ... | ... | ... | ... |

---

## Part 4: Pause Handling Test

**Goal**: Verify that TTS handles punctuation correctly and doesn't have excessive pauses.

### Test Sentences

Test these sentences and note if pauses are natural:

1. "Hello! How are you today?"
2. "What is artificial intelligence? It's a fascinating topic."
3. "I love learning! Don't you?"
4. "The answer is: yes, no, and maybe."
5. "Wait... let me think about that."

### Test Procedure

1. Type each test sentence
2. Listen to the TTS response
3. Note if pauses are:
   - Too long (awkward silence)
   - Too short (rushed)
   - Natural (appropriate timing)

### Pause Test Results

| Sentence | Provider | Voice | Pause Quality | Notes |
|----------|----------|-------|---------------|-------|
| 1 | ElevenLabs | _____ | ☐ Too Long ☐ Too Short ☐ Natural | _____ |
| 2 | ElevenLabs | _____ | ☐ Too Long ☐ Too Short ☐ Natural | _____ |
| 3 | Qwen | Serena | ☐ Too Long ☐ Too Short ☐ Natural | _____ |
| ... | ... | ... | ... | ... |

---

## Part 5: Voice Streaming Test

**Goal**: Verify that streaming mode works correctly (audio starts playing before full response is complete).

### Test Procedure

1. Open any bot dashboard
2. Enable streaming mode (if available)
3. Ask a long question that will generate a long response
4. Observe when audio starts playing
5. Check if audio continues smoothly

### Expected Behavior

- Audio should start playing within 1-2 seconds
- Audio should continue without interruption
- No gaps or stuttering between audio chunks

### Streaming Test Results

| Bot | Language | Provider | Audio Start Time | Smooth Playback? | Issues |
|-----|----------|----------|------------------|------------------|--------|
| Education | English | ElevenLabs | _____ sec | ☐ Yes ☐ No | _____ |
| ... | ... | ... | ... | ... | ... |

---

## Part 6: Cross-Language Voice Test

**Goal**: Verify that multi-language voices (like Serena, Ethan) work across different languages.

### Test Procedure

1. Select Qwen provider
2. Select "Serena" voice
3. Test with English: "Hello, this is a test"
4. Switch language to French
5. Test with French: "Bonjour, ceci est un test"
6. Switch to Chinese
7. Test with Chinese: "你好，这是一个测试"
8. Verify the voice sounds consistent across languages

### Cross-Language Test Results

| Voice | Language 1 | Language 2 | Language 3 | Consistent? | Notes |
|-------|------------|------------|------------|-------------|-------|
| Serena | English ☐ | French ☐ | Chinese ☐ | ☐ Yes ☐ No | _____ |
| Ethan | English ☐ | German ☐ | Spanish ☐ | ☐ Yes ☐ No | _____ |

---

## Part 7: Edge Cases and Error Handling

### Test Scenarios

1. **No microphone permission**
   - [ ] Error message is clear
   - [ ] User can retry after granting permission

2. **Network interruption during STT**
   - [ ] Error message appears
   - [ ] User can retry

3. **Network interruption during TTS**
   - [ ] Error message appears
   - [ ] User can retry

4. **Very long input (>500 words)**
   - [ ] System handles gracefully
   - [ ] Response is appropriate

5. **Empty/silent audio input**
   - [ ] System detects no speech
   - [ ] Appropriate message shown

6. **Background noise**
   - [ ] STT still works reasonably well
   - [ ] Or appropriate error message

### Edge Case Test Results

| Scenario | Handled Correctly? | Error Message Clear? | Notes |
|----------|-------------------|---------------------|-------|
| No mic permission | ☐ Yes ☐ No | ☐ Yes ☐ No | _____ |
| Network interruption (STT) | ☐ Yes ☐ No | ☐ Yes ☐ No | _____ |
| Network interruption (TTS) | ☐ Yes ☐ No | ☐ Yes ☐ No | _____ |
| Very long input | ☐ Yes ☐ No | ☐ Yes ☐ No | _____ |
| Silent audio | ☐ Yes ☐ No | ☐ Yes ☐ No | _____ |
| Background noise | ☐ Yes ☐ No | ☐ Yes ☐ No | _____ |

---

## Summary

### Overall Test Results

- **Total Tests Conducted**: _______
- **Tests Passed**: _______
- **Tests Failed**: _______
- **Pass Rate**: _______%

### Critical Issues Found

1. _______________________________________
2. _______________________________________
3. _______________________________________

### Minor Issues Found

1. _______________________________________
2. _______________________________________
3. _______________________________________

### Recommendations

1. _______________________________________
2. _______________________________________
3. _______________________________________

---

## Sign-off

**Tester Signature**: _______________________  
**Date**: _______________________  
**Status**: ☐ Approved ☐ Needs Fixes ☐ Blocked
