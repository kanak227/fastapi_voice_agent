'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Send, Trash, Loader2, Globe } from "lucide-react";
import { Sidebar } from '@/app/components/Sidebar';
import { VoiceOrb } from '@/components/voice-orb';
import { useVoiceChat } from '@/hooks/use-voice-chat';
import { streamRecordedVoiceTurn } from '@/lib/voice-streaming';
import { playAudioChunk } from '@/lib/audio-playback';
import { ChatMessage } from '@/components/chat-message';

import { TtsSettingsPanel } from '@/components/tts-settings-panel';
// Supported languages for voice input/output
const VOICE_LANGUAGES = [
  { code: 'en-US',    label: 'English',    flag: '🇺🇸' },
  { code: 'hi',       label: 'Hindi',      flag: '🇮🇳' },
  { code: 'hi-Latn',  label: 'Hinglish',   flag: '🇮🇳' },
  { code: 'ta',       label: 'Tamil',      flag: '🇮🇳' },
  { code: 'te',       label: 'Telugu',     flag: '🇮🇳' },
  { code: 'mr',       label: 'Marathi',    flag: '🇮🇳' },
  { code: 'bn',       label: 'Bengali',    flag: '🇮🇳' },
  { code: 'gu',       label: 'Gujarati',   flag: '🇮🇳' },
  { code: 'kn',       label: 'Kannada',    flag: '🇮🇳' },
  { code: 'ml',       label: 'Malayalam',  flag: '🇮🇳' },
  { code: 'pa',       label: 'Punjabi',    flag: '🇮🇳' },
  { code: 'fr',       label: 'French',     flag: '🇫🇷' },
  { code: 'de',       label: 'German',     flag: '🇩🇪' },
  { code: 'es',       label: 'Spanish',    flag: '🇪🇸' },
  { code: 'ar',       label: 'Arabic',     flag: '🇸🇦' },
  { code: 'zh',       label: 'Chinese',    flag: '🇨🇳' },
  { code: 'ja',       label: 'Japanese',   flag: '🇯🇵' },
];

export default function Dashboard() {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isClient, setIsClient] = useState(false);
  const [voiceError, setVoiceError] = useState('');
  /** idle | processing | speaking — voice pipeline only (no duplicate chat bubbles). */
  const [voicePhase, setVoicePhase] = useState('idle');
  const [handsFreeVoiceEnabled, setHandsFreeVoiceEnabled] = useState(false);
  const [voiceLanguage, setVoiceLanguage] = useState('en-US');
  const [showLangMenu, setShowLangMenu] = useState(false);
  const voiceLanguageRef = useRef('en-US');
  const isLoadingRef = useRef(false);
  const handsFreeEnabledRef = useRef(false);
  const voiceTurnActiveRef = useRef(false);
  const messagesEndRef = useRef(null);
  /** Track current audio element so we can stop playback mid-speech */
  const currentAudioRef = useRef(null);
  const voiceAbortRef = useRef(false);
  /** AbortController to cancel the SSE stream on stop */
  const voiceAbortControllerRef = useRef(null);
  /** Shared across typed chat and voice so FastAPI memory (session_id) stays consistent. */
  const voiceSessionIdRef = useRef(`global-citizenship-session-${Date.now()}`);

  // Initialize messages on client side only to prevent hydration mismatch
  useEffect(() => {
    setIsClient(true);
    setMessages([
      { id: 1, content: "Hello! I'm your Global Citizenship guide. Let's explore cultures, rights, and our shared world!", sender: "bot", time: formatTime(new Date()) },
    ]);
  }, []);

  // Consistent time formatting function
  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true
    });
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    isLoadingRef.current = isLoading;
  }, [isLoading]);

  useEffect(() => {
    handsFreeEnabledRef.current = handsFreeVoiceEnabled;
  }, [handsFreeVoiceEnabled]);

  useEffect(() => {
    if (!showLangMenu) return;
    const close = () => setShowLangMenu(false);
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, [showLangMenu]);

  useEffect(() => {
    voiceLanguageRef.current = voiceLanguage;
  }, [voiceLanguage]);

  const sendVoiceMessage = async (transcript) => {
    const text = (transcript || '').trim();
    if (!text || isLoadingRef.current) return;

    setMessages(prev => [
      ...prev,
      {
        id: Date.now(),
        content: text,
        sender: 'user',
        time: formatTime(new Date())
      }
    ]);

    await sendMessageToAPI(text);
  };

  const playBase64Audio = async (audioB64, mimeType = 'audio/mpeg') => {
    if (voiceAbortRef.current) return; // Skip if speech was stopped
    const audio = new Audio(`data:${mimeType};base64,${audioB64}`);
    currentAudioRef.current = audio;
    await new Promise((resolve) => {
      audio.onended = () => { currentAudioRef.current = null; resolve(); };
      audio.onerror = () => { currentAudioRef.current = null; resolve(); };
      audio.onpause = () => { currentAudioRef.current = null; resolve(); };
      audio.play().catch(() => { currentAudioRef.current = null; resolve(); });
    });
  };

  const stopVoicePlayback = () => {
    voiceAbortRef.current = true;
    // Abort the SSE fetch stream
    if (voiceAbortControllerRef.current) {
      voiceAbortControllerRef.current.abort();
      voiceAbortControllerRef.current = null;
    }
    // Stop current audio
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current.currentTime = 0;
      currentAudioRef.current = null;
    }
    setVoicePhase('idle');
  };

  const handleVoiceTurn = async ({ audio_b64, sample_rate_hz }) => {
    if (voiceTurnActiveRef.current) return;
    voiceTurnActiveRef.current = true;
    voiceAbortRef.current = false; // Reset abort flag for new turn
    try {
      setVoicePhase('processing');
      setVoiceError('');

      const isVoiceStopCommand = (rawText) => {
        const t = String(rawText || "").trim().toLowerCase();
        if (!t) return false;
        if (["no", "nah", "bye", "goodbye", "exit", "quit"].includes(t)) return true;
        if (["no thanks", "no thank you"].includes(t)) return true;
        if (
          t.includes("end chat") ||
          t.includes("end the chat") ||
          t.includes("stop chat") ||
          t.includes("stop the chat") ||
          t.includes("stop talking")
        )
          return true;
        if (t.startsWith("no ")) {
          const wc = t.split(/\s+/).filter(Boolean).length;
          if (wc <= 6) return true;
        }
        return false;
      };

      let didAddBotBubble = false;
      let botBubbleId = null;

      // Create abort controller for this voice turn
      const abortController = new AbortController();
      voiceAbortControllerRef.current = abortController;

      const turnResult = await streamRecordedVoiceTurn({
        session_id: voiceSessionIdRef.current,
        audio_b64,
        sample_rate_hz,
        domain: 'global-citizenship',
        language: voiceLanguageRef.current,
        stream: true,
        history: messages.map(m => ({
          role: m.sender === 'bot' ? 'assistant' : 'user',
          content: m.content
        })),
        abortSignal: abortController.signal,
        onTranscript: (t) => {
          const text = String(t || '').trim();
          if (!text) return;
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now() + Math.random(),
              content: text,
              sender: 'user',
              time: formatTime(new Date()),
            },
          ]);

          if (isVoiceStopCommand(text)) {
            setHandsFreeVoiceEnabled(false);
            handsFreeEnabledRef.current = false;
            stopListening({ finalize: false }).catch(() => {});
          }
        },
        onTextToken: (token) => {
          if (voiceAbortRef.current) return;
          // Stream original formatted text (with emojis, bold, etc.) in real-time
          if (!botBubbleId) {
            botBubbleId = Date.now() + Math.random();
            didAddBotBubble = true;
            setMessages((prev) => [
              ...prev,
              {
                id: botBubbleId,
                content: token,
                sender: 'bot',
                time: formatTime(new Date()),
              },
            ]);
          } else {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === botBubbleId
                  ? { ...msg, content: msg.content + token }
                  : msg
              )
            );
          }
        },
        onFinalText: (text) => {
          // Update bubble with final complete text (ensures nothing is missed)
          const reply = String(text || '').trim();
          if (!reply) return;
          if (botBubbleId) {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === botBubbleId ? { ...msg, content: reply } : msg
              )
            );
          } else if (!didAddBotBubble) {
            didAddBotBubble = true;
            botBubbleId = Date.now() + Math.random();
            setMessages((prev) => [
              ...prev,
              { id: botBubbleId, content: reply, sender: 'bot', time: formatTime(new Date()) },
            ]);
          }
        },
        onAudioChunk: async (chunk) => {
          if (voiceAbortRef.current) return;
          // Play audio (normalized text) concurrently while text streams
          setVoicePhase('speaking');
          await playAudioChunk(chunk, {
            shouldAbort: () => voiceAbortRef.current,
            onPlay: (audio) => { currentAudioRef.current = audio; },
          });
        },
      });

      // Fallback: if `final_text` wasn't parsed for any reason, add it once now.
      const fallbackBotText = String(turnResult?.final_text || "").trim();
      if (fallbackBotText && !didAddBotBubble) {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now() + Math.random(),
            content: fallbackBotText,
            sender: 'bot',
            time: formatTime(new Date()),
          },
        ]);
      }
    } catch (err) {
      // AbortError is expected when user stops playback — not an error
      if (err?.name !== 'AbortError') {
        setVoiceError(err?.message || 'Voice conversation failed.');
      }
    } finally {
      voiceTurnActiveRef.current = false;
      voiceAbortControllerRef.current = null;
      if (voicePhase !== 'idle') setVoicePhase('idle');
    }
  };

  const {
    isListening,
    isTranscribing,
    startListening,
    stopListening,
    supported: voiceSupported,
  } = useVoiceChat({
    // Voice pipeline uses FastAPI SSE (`event: input` + `event: final_text`) for chat bubbles.
    // Avoid wiring STT transcript here to prevent duplicate user messages.
    onTranscript: undefined,
    onAudioCaptured: handleVoiceTurn,
    onError: (msg) => setVoiceError(msg),
    language: voiceLanguageRef.current,
    manualMode: false,
  });

  const voiceHudMode = isListening
    ? 'listening'
    : voicePhase === 'speaking'
      ? 'speaking'
      : voicePhase === 'processing'
        ? 'processing'
        : 'idle';

const sendMessageToAPI = async (userMessage) => {
  try {
    setIsLoading(true);

    const historyPayload = messages.map(m => ({
      role: m.sender === 'bot' ? 'assistant' : 'user',
      content: m.content
    }));

    const response = await fetch("/api/GlobalCitizenship", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        query: userMessage,
        session_id: voiceSessionIdRef.current,
        history: historyPayload,
        language: voiceLanguageRef.current,
      }),
    });

    const data = await response.json();

    const botMessage = {
      id: Date.now() + Math.random(),
      content: data.response || "I'm sorry, I couldn't process your request.",
      sender: "bot",
      time: formatTime(new Date())
    };

    setMessages(prev => [...prev, botMessage]);
    return botMessage.content;
  } catch (error) {
    console.error("Error:", error);
    return "";
  } finally {
    setIsLoading(false);
  }
};


  const handleSendMessage = async () => {
    if (message.trim() && !isLoading && voicePhase === 'idle') {
      // Add user message to chat
      const userMessage = {
        id: Date.now(),
        content: message.trim(),
        sender: "user",
        time: formatTime(new Date())
      };

      setMessages(prev => [...prev, userMessage]);
      const messageToSend = message.trim();
      setMessage('');

      // Send to API
      await sendMessageToAPI(messageToSend);
    }
  };

  const handleVoiceOrbPress = async () => {
    try {
      // If currently speaking or processing, stop everything
      if (voicePhase === 'speaking' || voicePhase === 'processing') {
        stopVoicePlayback();
        return;
      }
      if (handsFreeEnabledRef.current) {
        setHandsFreeVoiceEnabled(false);
        await stopListening();
      } else {
        setHandsFreeVoiceEnabled(true);
        await startListening();
      }
    } catch (err) {
      setVoiceError(err?.message || 'Voice unavailable.');
      setHandsFreeVoiceEnabled(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const clearChat = () => {
    setHandsFreeVoiceEnabled(false);
    stopListening();
    voiceSessionIdRef.current = `global-citizenship-session-${Date.now()}`;
    setVoicePhase('idle');
    setVoiceError('');
    setMessages([
      { id: 1, content: "Hello! I'm your Global Citizenship guide. Let's explore cultures, rights, and our shared world!", sender: "bot", time: formatTime(new Date()) },
    ]);
  };

  // Don't render messages until client-side to prevent hydration mismatch
  if (!isClient) {
    return (
      <div className="flex h-screen w-full bg-zinc-800">
        <Sidebar />
        <div className="flex flex-col flex-1 min-w-0">
          <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-4 shadow-sm">
            <div className="flex items-center space-x-4">
              <h1 className="text-xl font-semibold text-gray-800">Global Citizenship AI</h1>
            </div>
            <div className="flex items-center space-x-3">
              <Avatar className="h-8 w-8">
                <AvatarImage src="/avatar.png" alt="User Avatar" />
                <AvatarFallback>JD</AvatarFallback>
              </Avatar>
            </div>
          </header>
          <main className="flex flex-1 overflow-hidden">
            <div className="flex-1 flex flex-col bg-gray-50">
              <div className="h-16 bg-white border-b border-gray-200 flex items-center justify-center">
                <div className="text-gray-500">Loading...</div>
              </div>
            </div>
          </main>
        </div>
      </div>
    );
  }

  const voiceOrbDisabled =
    !voiceSupported || isLoading;

  return (
    <div className="flex h-screen w-full bg-zinc-100">
      <Sidebar />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-200/80 bg-white px-4">
          <h1 className="text-[15px] font-semibold tracking-tight text-zinc-900">Global Citizenship AI</h1>
          <Avatar className="h-8 w-8">
            <AvatarImage src="/avatar.png" alt="" />
            <AvatarFallback className="bg-zinc-200 text-xs text-zinc-700">JD</AvatarFallback>
          </Avatar>
        </header>

        <main className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="flex min-h-0 flex-1 flex-col bg-white">
            <div className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-200/80 px-5">
              <div className="flex items-center gap-3">
                <Avatar className="h-9 w-9">
                  <AvatarFallback className="bg-zinc-900 text-[11px] font-medium text-white">
                    DA
                  </AvatarFallback>
                </Avatar>
                <div>
                  <h2 className="text-[15px] font-medium text-zinc-900">Assistant</h2>
                  <p className="text-xs text-zinc-500">
                    {voiceHudMode === 'listening'
                      ? 'Listening'
                      : voiceHudMode === 'processing'
                        ? 'Processing'
                        : voiceHudMode === 'speaking'
                          ? 'Playing reply'
                          : isLoading
                            ? 'Thinking…'
                            : 'Ready'}
                  </p>
                </div>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="text-zinc-600 hover:text-zinc-900"
                onClick={clearChat}
              >
                <Trash className="mr-2 h-4 w-4" />
                Clear
              </Button>
            </div>

            <div className="custom-scrollbar min-h-0 flex-1 overflow-y-auto px-4 py-5">
              <div className="mx-auto max-w-3xl space-y-5">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${
                        msg.sender === 'user'
                          ? 'rounded-br-md bg-zinc-800 text-zinc-50'
                          : 'rounded-bl-md border border-zinc-200/80 bg-zinc-50/80 text-zinc-800 shadow-sm'
                      }`}
                    >
                      <ChatMessage content={msg.content} isBot={msg.sender === 'bot'} />
                      <p
                        className={`mt-1.5 text-[11px] tabular-nums ${
                          msg.sender === 'user' ? 'text-zinc-400' : 'text-zinc-400'
                        }`}
                      >
                        {msg.time}
                      </p>
                    </div>
                  </div>
                ))}

                {isLoading && (
                  <div className="flex justify-start">
                    <div className="flex items-center gap-2 rounded-2xl rounded-bl-md border border-zinc-200/80 bg-white px-4 py-2.5 text-sm text-zinc-500">
                      <Loader2 className="h-4 w-4 shrink-0 animate-spin text-zinc-400" />
                      <span>Thinking…</span>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>

            <div className="border-t border-zinc-200/80 bg-zinc-50/90 px-4 py-3">
              <div className="mx-auto max-w-3xl">
                {/* Language selector row */}
                <div className="mb-2 flex items-center gap-2">
                  <div className="relative">
                    <button
                      type="button"
                      onClick={() => setShowLangMenu(prev => !prev)}
                      className="flex items-center gap-1.5 rounded-lg border border-zinc-200 bg-white px-2.5 py-1.5 text-xs font-medium text-zinc-700 hover:border-zinc-300 hover:bg-zinc-50 transition-colors"
                    >
                      <Globe className="h-3.5 w-3.5 text-zinc-500" />
                      <span>{VOICE_LANGUAGES.find(l => l.code === voiceLanguage)?.flag}</span>
                      <span>{VOICE_LANGUAGES.find(l => l.code === voiceLanguage)?.label}</span>
                      <span className="text-zinc-400">▾</span>
                    </button>
                    {showLangMenu && (
                      <div className="absolute bottom-full left-0 mb-1 z-50 w-44 rounded-xl border border-zinc-200 bg-white shadow-lg overflow-hidden">
                        <div className="max-h-64 overflow-y-auto py-1">
                          {VOICE_LANGUAGES.map(lang => (
                            <button
                              key={lang.code}
                              type="button"
                              onClick={() => { setVoiceLanguage(lang.code); setShowLangMenu(false); }}
                              className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-zinc-50 transition-colors ${voiceLanguage === lang.code ? 'bg-zinc-100 font-medium text-zinc-900' : 'text-zinc-700'}`}
                            >
                              <span>{lang.flag}</span>
                              <span>{lang.label}</span>
                              {voiceLanguage === lang.code && <span className="ml-auto text-zinc-400">✓</span>}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <span className="text-xs text-zinc-400">Voice language</span>
                  <TtsSettingsPanel className="ml-auto" language={voiceLanguage} />
                </div>
                <div className="flex items-end gap-2">
                  <VoiceOrb
                    state={voiceHudMode}
                    disabled={voiceOrbDisabled}
                    onClick={handleVoiceOrbPress}
                  />
                  <div className="relative min-w-0 flex-1">
                    <textarea
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder="Message…"
                      disabled={isLoading || voicePhase !== 'idle'}
                      rows={1}
                      className="min-h-[48px] w-full resize-none rounded-xl border border-zinc-200 bg-white px-4 py-3 text-[15px] text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-300 focus:outline-none focus:ring-2 focus:ring-zinc-200/80 max-h-32"
                      style={{ height: 'auto', minHeight: '48px' }}
                      onInput={(e) => {
                        e.target.style.height = 'auto';
                        e.target.style.height = `${Math.min(e.target.scrollHeight, 128)}px`;
                      }}
                    />
                  </div>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={handleSendMessage}
                    disabled={!message.trim() || isLoading || voicePhase !== 'idle'}
                    className="h-12 w-12 shrink-0 rounded-xl border border-zinc-200 bg-zinc-900 text-white hover:bg-zinc-800 disabled:opacity-40"
                  >
                    {isLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                {voiceError && (
                  <p className="mt-2 text-xs text-red-600">{voiceError}</p>
                )}
                {!voiceSupported && (
                  <p className="mt-2 text-xs text-zinc-500">Voice input is not available in this browser.</p>
                )}
                {isListening && (
                  <p className="mt-2 text-xs text-zinc-500">Tap the microphone again to stop and send.</p>
                )}
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}