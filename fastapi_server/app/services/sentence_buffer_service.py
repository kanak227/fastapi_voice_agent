"""Streaming sentence buffer for TTS chunking.

The LLM emits text token by token. We collect it into a buffer and pop
TTS-ready chunks at sentence boundaries, so the speech provider can
synthesize while the rest of the response is still streaming.

Why per-provider chunk sizes:
  - ElevenLabs streams audio internally during generation, so emitting
    one TTS call per sentence is fine and gives the user audio earlier.
  - Self-hosted Qwen3 cannot stream — every call returns the full clip
    after ~5-8s on a T4. Per-sentence chunks introduce audible gaps
    between clips. Sending a single larger chunk (~80 words) keeps the
    audio continuous.
"""

from __future__ import annotations

import re

# Match complete sentences ending with .!? followed by whitespace or end of string.
# Conservative pattern: avoids false-positive splits on abbreviations like
# "e.g." or numeric points like "v1.0" by requiring a sentence end to be
# followed by whitespace AND start with a non-alphanumeric / capital token,
# but keeping the simple variant (handles 99% of LLM output) until the
# regression suite proves we need fancier handling.
_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]+(?=\s|$)")

# Soft break points within a long run-on sentence: comma, semicolon, em dash.
_SOFT_BREAK_RE = re.compile(r"(?<=[,;])\s+")

DEFAULT_MAX_CHUNK_WORDS = 40        # ElevenLabs / cloud providers: per-sentence
QWEN_MAX_CHUNK_WORDS = 80           # Self-hosted: bigger chunks → fewer gaps
QWEN_FIRST_CHUNK_WORDS = 16         # Self-hosted: tiny first chunk → fast first audio


class SentenceBufferService:
    """Splits assistant text into TTS-friendly sentence chunks."""

    def split_for_tts(
        self,
        text: str,
        *,
        max_chunk_words: int = DEFAULT_MAX_CHUNK_WORDS,
    ) -> list[str]:
        """Split text into TTS-friendly chunks.

        ``max_chunk_words`` controls how aggressively we coalesce short
        sentences into one chunk. For Qwen3 we pass a higher value so the
        whole reply tends to fit in a single synthesis call.
        """
        content = (text or "").strip()
        if not content:
            return []

        base_sentences = [m.group(0).strip() for m in _SENTENCE_RE.finditer(content)]
        if not base_sentences:
            base_sentences = [content if content[-1] in ".!?" else f"{content}."]

        chunks: list[str] = []
        running: list[str] = []
        running_word_count = 0

        def _flush() -> None:
            nonlocal running, running_word_count
            if not running:
                return
            chunk = " ".join(running).strip().rstrip(" ,;:-")
            if chunk and chunk[-1] not in ".!?":
                chunk += "."
            chunks.append(chunk)
            running = []
            running_word_count = 0

        for sentence in base_sentences:
            words = sentence.split()
            # Try to merge short sentences with the previous chunk.
            if running_word_count + len(words) <= max_chunk_words:
                running.append(sentence)
                running_word_count += len(words)
                continue

            # Sentence is too long alone — split it at soft break points.
            if not running:
                parts = _SOFT_BREAK_RE.split(sentence)
                inner_running: list[str] = []
                inner_words = 0
                for part in parts:
                    pw = len(part.split())
                    if inner_running and inner_words + pw > max_chunk_words:
                        chunk = " ".join(inner_running).strip().rstrip(" ,;:-")
                        if chunk and chunk[-1] not in ".!?":
                            chunk += "."
                        chunks.append(chunk)
                        inner_running = [part]
                        inner_words = pw
                    else:
                        inner_running.append(part)
                        inner_words += pw
                if inner_running:
                    running = inner_running
                    running_word_count = inner_words
            else:
                # Flush the current pile, start fresh with this big sentence.
                _flush()
                running = [sentence]
                running_word_count = len(words)

        _flush()
        return [c for c in chunks if c.strip()]

    def pop_leading_speech_chunks(
        self,
        buffer: str,
        *,
        max_chunk_words: int = DEFAULT_MAX_CHUNK_WORDS,
    ) -> tuple[list[str], str]:
        """Pop complete leading sentences from ``buffer`` as TTS chunks.

        Returns ``(chunks, remainder)`` so the caller can keep accumulating
        the remainder until the next sentence boundary arrives.
        """
        chunks_out: list[str] = []
        rest = buffer or ""
        pending: list[str] = []
        pending_words = 0

        while True:
            m = _SENTENCE_RE.match(rest)
            if not m:
                break
            sentence = m.group(0).strip()
            rest = rest[m.end():].lstrip()
            words = sentence.split()
            # Keep stacking sentences until the chunk is full, then emit.
            if pending_words + len(words) <= max_chunk_words:
                pending.append(sentence)
                pending_words += len(words)
                continue
            if pending:
                chunks_out.append(" ".join(pending))
                pending = []
                pending_words = 0
            # The current sentence might still be huge on its own.
            chunks_out.extend(self.split_for_tts(sentence, max_chunk_words=max_chunk_words))

        if pending:
            chunks_out.append(" ".join(pending))
        return chunks_out, rest


sentence_buffer_service = SentenceBufferService()
