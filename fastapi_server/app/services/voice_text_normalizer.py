"""
Voice Text Normalizer Service

Transforms LLM-generated text (with markdown, emojis, special formatting) into
clean, natural speech-ready text for TTS synthesis. Applied per-sentence before
sending to the speech provider.
"""

from __future__ import annotations

import re


# Emoji unicode ranges (covers most common emoji blocks)
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F9FF"  # Misc Symbols, Emoticons, Dingbats, etc.
    "\U00002600-\U000026FF"  # Misc Symbols
    "\U00002700-\U000027BF"  # Dingbats
    "\U0000FE00-\U0000FE0F"  # Variation Selectors
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "\U0000200D"             # Zero Width Joiner
    "\U000000A9"             # Copyright
    "\U000000AE"             # Registered
    "\U0000203C-\U00003299"  # CJK Symbols, Enclosed CJK
    "]+",
    flags=re.UNICODE,
)

# Markdown bold/italic: **text** or *text* or __text__ or _text_
_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_MD_BOLD_UNDER_RE = re.compile(r"__(.+?)__")
_MD_ITALIC_UNDER_RE = re.compile(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)")

# Markdown headers: ## Header or ### Header
_MD_HEADER_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)

# Markdown bullet points and numbered lists
_MD_BULLET_RE = re.compile(r"^[\s]*[-•*]\s+", re.MULTILINE)
_MD_NUMBERED_RE = re.compile(r"^[\s]*\d+[.)]\s+", re.MULTILINE)

# Markdown links: [text](url) → keep text only
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")

# Markdown inline code: `code` → keep code text
_MD_INLINE_CODE_RE = re.compile(r"`([^`]+)`")

# Markdown code blocks: ```...``` → remove entirely
_MD_CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)

# Markdown blockquotes: > text
_MD_BLOCKQUOTE_RE = re.compile(r"^>\s*", re.MULTILINE)

# Markdown horizontal rules: --- or *** or ___
_MD_HR_RE = re.compile(r"^[-*_]{3,}\s*$", re.MULTILINE)

# Multiple newlines → single space (for speech flow)
_MULTI_NEWLINE_RE = re.compile(r"\n{2,}")
_SINGLE_NEWLINE_RE = re.compile(r"\n")

# Multiple spaces
_MULTI_SPACE_RE = re.compile(r" {2,}")

# Common abbreviations that TTS might mispronounce — expand them
_ABBREVIATIONS: dict[str, str] = {
    "e.g.": "for example",
    "i.e.": "that is",
    "etc.": "and so on",
    "vs.": "versus",
    "Dr.": "Doctor",
    "Mr.": "Mister",
    "Mrs.": "Missus",
    "Ms.": "Miss",
    "Prof.": "Professor",
    "approx.": "approximately",
    "govt.": "government",
    "dept.": "department",
}

# Special characters that should be spoken or removed
_SPECIAL_CHARS = {
    "→": "leads to",
    "←": "comes from",
    "↔": "goes both ways",
    "•": "",
    "·": "",
    "—": ", ",
    "–": ", ",
    "…": ", ",
    "\"": "",
    "'": "'",
    "'": "'",
    """: "",
    """: "",
    "✓": "yes",
    "✗": "no",
    "✘": "no",
    "©": "copyright",
    "®": "registered",
    "™": "trademark",
    "&": "and",
}


class VoiceTextNormalizer:
    """
    Normalizes LLM output text into clean, natural speech for TTS.

    Call `normalize(text)` on each sentence/chunk before passing to the TTS provider.
    """

    def normalize(self, text: str) -> str:
        """
        Full normalization pipeline: markdown → emojis → special chars → whitespace.

        Args:
            text: Raw text from LLM (may contain markdown, emojis, etc.)

        Returns:
            Clean text suitable for TTS synthesis.
        """
        if not text or not text.strip():
            return ""

        result = text

        # 1. Remove code blocks first (they shouldn't be spoken)
        result = _MD_CODE_BLOCK_RE.sub("", result)

        # 2. Strip markdown formatting (keep the text content)
        result = _MD_BOLD_RE.sub(r"\1", result)
        result = _MD_ITALIC_RE.sub(r"\1", result)
        result = _MD_BOLD_UNDER_RE.sub(r"\1", result)
        result = _MD_ITALIC_UNDER_RE.sub(r"\1", result)
        result = _MD_HEADER_RE.sub("", result)
        result = _MD_BULLET_RE.sub("", result)
        result = _MD_NUMBERED_RE.sub("", result)
        result = _MD_LINK_RE.sub(r"\1", result)
        result = _MD_INLINE_CODE_RE.sub(r"\1", result)
        result = _MD_BLOCKQUOTE_RE.sub("", result)
        result = _MD_HR_RE.sub("", result)

        # 3. Remove emojis
        result = _EMOJI_RE.sub("", result)

        # 4. Replace special characters
        for char, replacement in _SPECIAL_CHARS.items():
            result = result.replace(char, replacement)

        # 5. Expand common abbreviations
        for abbr, expansion in _ABBREVIATIONS.items():
            result = result.replace(abbr, expansion)

        # 6. Normalize whitespace
        result = _MULTI_NEWLINE_RE.sub(". ", result)
        result = _SINGLE_NEWLINE_RE.sub(" ", result)
        result = _MULTI_SPACE_RE.sub(" ", result)

        # 7. Clean up punctuation artifacts
        # Remove double periods, but preserve exclamation marks and question marks
        result = re.sub(r"\.{2,}", ".", result)
        result = re.sub(r",\s*\.", ".", result)
        result = re.sub(r"\.\s*,", ".", result)
        result = re.sub(r"^\s*[.,;:]\s*", "", result)
        # Strip orphan punctuation left by emoji/markdown removal:
        # double spaces, " . " in the middle of text, " , ," etc.
        # But preserve ! and ? for natural speech intonation
        result = re.sub(r"\s+([,.;:])", r"\1", result)
        result = re.sub(r"([,.;:])\s*([,.;:])", r"\1", result)
        # Normalize multiple exclamation/question marks to single ones
        result = re.sub(r"!{2,}", "!", result)
        result = re.sub(r"\?{2,}", "?", result)
        # Add slight pause after exclamation/question marks if followed by text
        result = re.sub(r"([!?])([A-Za-z])", r"\1 \2", result)
        result = _MULTI_SPACE_RE.sub(" ", result)

        return result.strip()

    def normalize_sentence(self, sentence: str) -> str:
        """
        Normalize a single sentence for TTS. Lighter version that preserves
        sentence boundaries.
        """
        normalized = self.normalize(sentence)
        if not normalized:
            return ""
        # Ensure sentence ends with proper punctuation
        if normalized and normalized[-1] not in ".!?":
            normalized += "."
        return normalized


# Singleton instance
voice_text_normalizer = VoiceTextNormalizer()
