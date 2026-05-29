"""
Voice Text Normalizer Service
==============================

Transforms LLM-generated text (markdown, emojis, digits, symbols) into clean,
natural, *speakable* text for TTS synthesis. Applied per sentence/chunk before
the text is sent to the speech engine.

Why this exists
---------------
The TTS engines we run (Meta MMS-TTS for Indian/regional languages and
Qwen3-TTS for English/CJK/European) are plain neural text-to-speech models.
They read whatever characters they are given. If you hand them "₹1,25,000" or
"25%" or "9876543210" they mispronounce or skip it, and they do not understand
prosody control tags such as ``[LPAUSE]`` or ``[EMPH]`` — they would literally
*say* the word "LPAUSE".

So "human-like" speech here comes from two things, both handled below:

1. **Language-aware text normalization** — numbers, currency, percentages,
   decimals, times, long digit runs (phone/OTP) and acronyms are converted into
   spoken words *in the target language* (Hindi digits become Hindi words, Tamil
   become Tamil, etc.). This is the part that was previously missing and is the
   main reason non-English speech sounded wrong.
2. **Prosody through real punctuation** — commas, periods, question and
   exclamation marks are preserved/cleaned so the engine's own prosody model
   produces natural pauses and intonation. We do NOT inject bracket tags.

Number-to-words uses two libraries:
- ``indic-numtowords`` (AI4Bharat, MIT) for Indian languages — it understands
  the Indian numbering system (lakh / crore).
- ``num2words`` for English / European / CJK languages.
Both are optional: if a conversion fails we fall back to the raw digits so the
pipeline never crashes.
"""

from __future__ import annotations

import re

# --- Optional number-to-words backends ------------------------------------
# Imported defensively so a missing wheel never breaks TTS; we just fall back
# to leaving digits as-is for that language.
try:  # Indian languages (hi, ta, te, mr, bn, gu, kn, ml, pa, ur, ...)
    from indic_numtowords import num2words as _indic_num2words  # type: ignore
    _INDIC_OK = True
except Exception:  # pragma: no cover - import guard
    _indic_num2words = None  # type: ignore
    _INDIC_OK = False

try:  # English / European / CJK
    from num2words import num2words as _western_num2words  # type: ignore
    _WESTERN_OK = True
except Exception:  # pragma: no cover - import guard
    _western_num2words = None  # type: ignore
    _WESTERN_OK = False


# ---------------------------------------------------------------------------
# Markdown / emoji / formatting patterns (language-agnostic)
# ---------------------------------------------------------------------------

_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F9FF"  # Misc Symbols, Emoticons, Dingbats, etc.
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "\U00002600-\U000026FF"  # Misc Symbols
    "\U00002700-\U000027BF"  # Dingbats
    "\U00002B00-\U00002BFF"  # Misc Symbols and Arrows (stars, etc.)
    "\U0001F000-\U0001F0FF"  # Mahjong / Dominoes / Playing Cards
    "\U0001F100-\U0001F1FF"  # Enclosed Alphanumeric Supplement (flags)
    "\U0000FE00-\U0000FE0F"  # Variation Selectors
    "\U0000200D"             # Zero Width Joiner
    "\U000020E3"             # Combining Enclosing Keycap
    "\U00002122"             # Trademark
    "\U00002139"             # Information
    "\U0000203C"             # Double exclamation
    "\U00002049"             # Exclamation question
    "\U000000A9"             # Copyright
    "\U000000AE"             # Registered
    "]+",
    flags=re.UNICODE,
)

_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_MD_BOLD_UNDER_RE = re.compile(r"__(.+?)__")
_MD_ITALIC_UNDER_RE = re.compile(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)")
_MD_HEADER_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_MD_BULLET_RE = re.compile(r"^[\s]*[-•*]\s+", re.MULTILINE)
_MD_NUMBERED_RE = re.compile(r"^[\s]*\d+[.)]\s+", re.MULTILINE)
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_MD_CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_MD_BLOCKQUOTE_RE = re.compile(r"^>\s*", re.MULTILINE)
_MD_HR_RE = re.compile(r"^[-*_]{3,}\s*$", re.MULTILINE)
_MULTI_NEWLINE_RE = re.compile(r"\n{2,}")
_SINGLE_NEWLINE_RE = re.compile(r"\n")
_MULTI_SPACE_RE = re.compile(r" {2,}")

# English abbreviations expanded only for English (injecting these English words
# into another language would sound wrong).
_EN_ABBREVIATIONS: dict[str, str] = {
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

# Punctuation / symbol replacements that are safe across languages. The "&"
# connector is handled per-language via the profile (see below).
_SPECIAL_CHARS = {
    "→": ", ",
    "←": ", ",
    "↔": ", ",
    "•": "",
    "·": "",
    "—": ", ",
    "–": ", ",
    "…": ", ",
    "\u201c": "",
    "\u201d": "",
    "\u2018": "'",
    "\u2019": "'",
    "✓": "",
    "✗": "",
    "✘": "",
    "©": "",
    "®": "",
    "™": "",
}


# ---------------------------------------------------------------------------
# Per-language profiles
# ---------------------------------------------------------------------------
# base code -> {
#   "num":    code passed to the number library
#   "indic":  True -> use indic-numtowords, False -> use num2words
#   "point":  decimal-point word (None -> leave decimals as digits)
#   "percent":word spoken for "%"
#   "and":    connector between major/minor currency units
#   "currency": { symbol: (major_word, minor_word) }
# }
# Indian-language number words are produced by indic-numtowords (lakh/crore
# system); everything else by num2words.

_RUPEE = ("rupees", "paise")

LANG_PROFILES: dict[str, dict] = {
    "en": {
        "num": "en", "indic": False, "point": "point", "percent": "percent",
        "and": "and",
        "currency": {"₹": _RUPEE, "$": ("dollars", "cents"),
                      "€": ("euros", "cents"), "£": ("pounds", "pence")},
    },
    "hi": {
        "num": "hi", "indic": True, "point": "दशमलव", "percent": "प्रतिशत",
        "and": "और",
        "currency": {"₹": ("रुपये", "पैसे"), "$": ("डॉलर", "सेंट"),
                      "€": ("यूरो", "सेंट"), "£": ("पाउंड", "पेंस")},
    },
    "ta": {
        "num": "ta", "indic": True, "point": None, "percent": "சதவீதம்",
        "and": "மற்றும்",
        "currency": {"₹": ("ரூபாய்", "பைசா"), "$": ("டாலர்", "சென்ட்")},
    },
    "te": {
        "num": "te", "indic": True, "point": None, "percent": "శాతం",
        "and": "మరియు",
        "currency": {"₹": ("రూపాయలు", "పైసలు"), "$": ("డాలర్లు", "సెంట్లు")},
    },
    "mr": {
        "num": "mr", "indic": True, "point": "दशांश", "percent": "टक्के",
        "and": "आणि",
        "currency": {"₹": ("रुपये", "पैसे"), "$": ("डॉलर", "सेंट")},
    },
    "bn": {
        "num": "bn", "indic": True, "point": None, "percent": "শতাংশ",
        "and": "এবং",
        "currency": {"₹": ("টাকা", "পয়সা"), "$": ("ডলার", "সেন্ট")},
    },
    "gu": {
        "num": "gu", "indic": True, "point": None, "percent": "ટકા",
        "and": "અને",
        "currency": {"₹": ("રૂપિયા", "પૈસા"), "$": ("ડોલર", "સેન્ટ")},
    },
    "kn": {
        "num": "kn", "indic": True, "point": None, "percent": "ಶೇಕಡಾ",
        "and": "ಮತ್ತು",
        "currency": {"₹": ("ರೂಪಾಯಿ", "ಪೈಸೆ"), "$": ("ಡಾಲರ್", "ಸೆಂಟ್")},
    },
    "ml": {
        "num": "ml", "indic": True, "point": None, "percent": "ശതമാനം",
        "and": "ഒപ്പം",
        "currency": {"₹": ("രൂപ", "പൈസ"), "$": ("ഡോളർ", "സെന്റ്")},
    },
    "pa": {
        "num": "pa", "indic": True, "point": None, "percent": "ਪ੍ਰਤੀਸ਼ਤ",
        "and": "ਅਤੇ",
        "currency": {"₹": ("ਰੁਪਏ", "ਪੈਸੇ"), "$": ("ਡਾਲਰ", "ਸੈਂਟ")},
    },
    "ur": {
        "num": "ur", "indic": True, "point": None, "percent": "فیصد",
        "and": "اور",
        "currency": {"₹": ("روپے", "پیسے"), "$": ("ڈالر", "سینٹ")},
    },
    "ar": {
        "num": "ar", "indic": False, "point": "فاصلة", "percent": "بالمئة",
        "and": "و",
        "currency": {"$": ("دولار", "سنت"), "€": ("يورو", "سنت"), "₹": ("روبية", "بيسة")},
    },
    "fr": {
        "num": "fr", "indic": False, "point": "virgule", "percent": "pour cent",
        "and": "et",
        "currency": {"€": ("euros", "centimes"), "$": ("dollars", "cents"),
                      "£": ("livres", "pence")},
    },
    "de": {
        "num": "de", "indic": False, "point": "Komma", "percent": "Prozent",
        "and": "und",
        "currency": {"€": ("Euro", "Cent"), "$": ("Dollar", "Cent"),
                      "£": ("Pfund", "Pence")},
    },
    "es": {
        "num": "es", "indic": False, "point": "coma", "percent": "por ciento",
        "and": "y",
        "currency": {"€": ("euros", "céntimos"), "$": ("dólares", "centavos")},
    },
    "ja": {
        "num": "ja", "indic": False, "point": None, "percent": "パーセント",
        "and": "と",
        "currency": {"¥": ("円", ""), "$": ("ドル", "セント")},
    },
    "zh": {
        "num": "zh", "indic": False, "point": None, "percent": "百分之",
        "and": "和",
        "currency": {"¥": ("元", ""), "$": ("美元", "美分")},
    },
}

# Spoken month names per language, indexed 1..12. Languages absent here fall
# back to speaking the month *number* as a cardinal.
_MONTHS: dict[str, list[str]] = {
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
    "hi": ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई",
           "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"],
    "mr": ["जानेवारी", "फेब्रुवारी", "मार्च", "एप्रिल", "मे", "जून", "जुलै",
           "ऑगस्ट", "सप्टेंबर", "ऑक्टोबर", "नोव्हेंबर", "डिसेंबर"],
}

# Spoken names of the Latin letters A-Z, for reading acronyms (AI, OTP, GPS...)
# in a given script. English keeps the letters spaced; Hindi maps to Devanagari
# letter names so the MMS Hindi tokenizer (which expects Devanagari) can voice
# them instead of dropping the Latin characters.
_LETTER_NAMES: dict[str, dict[str, str]] = {
    "hi": {
        "A": "ए", "B": "बी", "C": "सी", "D": "डी", "E": "ई", "F": "एफ़",
        "G": "जी", "H": "एच", "I": "आई", "J": "जे", "K": "के", "L": "एल",
        "M": "एम", "N": "एन", "O": "ओ", "P": "पी", "Q": "क्यू", "R": "आर",
        "S": "एस", "T": "टी", "U": "यू", "V": "वी", "W": "डब्ल्यू",
        "X": "एक्स", "Y": "वाई", "Z": "ज़ेड",
    },
}

# Acronyms we deliberately spell out letter-by-letter. We use a curated set
# rather than "any run of capitals" so real all-caps words (STOP, OK) and
# word-acronyms normally read as words (NASA, UNESCO) are left alone.
_SPELL_OUT_ACRONYMS: set[str] = {
    "AI", "API", "OTP", "URL", "GPS", "ID", "PIN", "OK", "FAQ", "PDF", "HTML",
    "HTTP", "HTTPS", "USB", "SMS", "PDFs", "CEO", "CFO", "CTO", "HR", "IT",
    "UI", "UX", "QR", "ATM", "KYC", "UPI", "GST", "PAN", "IFSC", "EMI", "RBI",
    "SIM", "OS", "PC", "TV", "DVD", "CD", "FM", "AM", "PM", "USA", "UK", "UAE",
    "EU", "UN", "WHO", "GDP", "IQ", "EQ", "DIY", "FYI", "ASAP", "RSVP",
}
_ACRONYM_RE = re.compile(r"\b([A-Z]{2,}s?)\b")
# Date: DD/MM/YYYY or DD-MM-YYYY (also accepts D/M/YY).
_DATE_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b")
# Currency: symbol then a number, optionally with decimals. e.g. ₹1,25,000.50
_CURRENCY_RE = re.compile(r"([₹$€£¥])\s?(\d[\d,]*)(?:\.(\d+))?")
# Currency suffix form (European): number then symbol. e.g. 1.500,50€ / 1500€
_CURRENCY_SUFFIX_RE = re.compile(r"(\d[\d,]*)(?:\.(\d+))?\s?([₹$€£¥])")
# Percentage: number (optionally decimal) followed by %.
_PERCENT_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s?%")
# Clock time: H:MM with optional AM/PM.
_TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\s*([AaPp][Mm])?\b")
# Decimal number (not already consumed by currency/percent).
_DECIMAL_RE = re.compile(r"\b(\d+)\.(\d+)\b")
# Long bare digit run (phone numbers, long IDs) -> read digit by digit.
_LONG_DIGITS_RE = re.compile(r"\b\d{7,}\b")
# Remaining plain integers, allowing thousands separators.
_INTEGER_RE = re.compile(r"\b\d[\d,]*\b")


def _base_lang(language: str | None) -> str:
    """Normalize an incoming language code to a profile key.

    'en-US' -> 'en', 'hi-Latn' -> 'hi' (romanized Hindi voices in Hindi),
    unknown -> 'en'.
    """
    if not language:
        return "en"
    code = language.strip().lower().replace("_", "-")
    # Hinglish: romanized Hindi. Numbers should be spoken as Hindi words; the
    # downstream MMS path transliterates Latin->Devanagari and leaves the
    # Devanagari number words untouched.
    if code in ("hi-latn", "hi-latin"):
        return "hi"
    base = code.split("-")[0]
    return base if base in LANG_PROFILES else "en"


def _cardinal(num: int, profile: dict) -> str:
    """Convert an integer to words in the profile's language, with fallback."""
    if num < 0:
        return "-" + _cardinal(-num, profile)
    code = profile["num"]
    if profile.get("indic") and _INDIC_OK:
        try:
            return str(_indic_num2words(num, lang=code))
        except Exception:
            pass
    if _WESTERN_OK:
        try:
            return str(_western_num2words(num, lang=code))
        except Exception:
            pass
    # Last resort: leave the digits so nothing is lost.
    return str(num)


def _digit_by_digit(digits: str, profile: dict) -> str:
    """Read each digit individually (phone numbers, OTPs, long IDs)."""
    return " ".join(_cardinal(int(d), profile) for d in digits if d.isdigit())


class VoiceTextNormalizer:
    """Normalizes LLM output into clean, natural, language-aware speech text."""

    # -- public API ---------------------------------------------------------

    def normalize(self, text: str, language: str | None = None) -> str:
        """Full normalization pipeline.

        Args:
            text: Raw text from the LLM (markdown, emojis, digits, symbols...).
            language: BCP-47-ish code ('hi', 'en-US', 'ta', ...). Drives which
                language the numbers/currency/etc. are spoken in. Defaults to
                English when omitted (backwards compatible).

        Returns:
            Clean text ready for the TTS engine.
        """
        if not text or not text.strip():
            return ""

        base = _base_lang(language)
        profile = LANG_PROFILES.get(base, LANG_PROFILES["en"])
        result = text

        # 1. Remove code blocks (never spoken).
        result = _MD_CODE_BLOCK_RE.sub("", result)

        # 2. Strip markdown formatting, keep the text content.
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

        # 3. Remove emojis.
        result = _EMOJI_RE.sub("", result)

        # 4. Language-aware numeric normalization. Order matters: currency and
        #    percent own their trailing/leading symbol, times own the colon,
        #    decimals before integers, long digit runs before short ones.
        result = self._normalize_numbers(result, profile)

        # 5. Acronyms (AI, OTP, URL...) -> spoken letters in the target script.
        result = self._normalize_acronyms(result, base)

        # 6. Symbols. "&" uses the language's connector word.
        result = result.replace("&", f" {profile['and']} ")
        for char, replacement in _SPECIAL_CHARS.items():
            result = result.replace(char, replacement)

        # 7. English abbreviations (English only).
        if base == "en":
            for abbr, expansion in _EN_ABBREVIATIONS.items():
                result = result.replace(abbr, expansion)

        # 8. Whitespace + punctuation cleanup. Punctuation is preserved so the
        #    engine's prosody produces natural pauses/intonation.
        result = self._cleanup(result)
        return result.strip()

    def normalize_sentence(self, sentence: str, language: str | None = None) -> str:
        """Normalize a single sentence, ensuring terminal punctuation so the
        engine applies a sentence-final cadence."""
        normalized = self.normalize(sentence, language)
        if not normalized:
            return ""
        if normalized[-1] not in ".!?。！？।۔":
            normalized += "."
        return normalized

    # -- internals ----------------------------------------------------------

    def _normalize_numbers(self, text: str, profile: dict) -> str:
        def _date(m: re.Match) -> str:
            return self._date_words(m.group(1), m.group(2), m.group(3), profile)

        def _currency(m: re.Match) -> str:
            symbol, whole, frac = m.group(1), m.group(2), m.group(3)
            return self._currency_words(symbol, whole, frac, profile, m.group(0))

        def _currency_suffix(m: re.Match) -> str:
            whole, frac, symbol = m.group(1), m.group(2), m.group(3)
            return self._currency_words(symbol, whole, frac, profile, m.group(0))

        def _percent(m: re.Match) -> str:
            num = m.group(1)
            if "." in num:
                whole, frac = num.split(".", 1)
                spoken = self._decimal_words(whole, frac, profile)
            else:
                spoken = _cardinal(int(num.replace(",", "")), profile)
            return f"{spoken} {profile['percent']}"

        def _time(m: re.Match) -> str:
            hour, minute, ampm = int(m.group(1)), int(m.group(2)), m.group(3)
            return self._time_words(hour, minute, ampm, profile)

        def _decimal(m: re.Match) -> str:
            return self._decimal_words(m.group(1), m.group(2), profile)

        def _long(m: re.Match) -> str:
            return _digit_by_digit(m.group(0), profile)

        def _integer(m: re.Match) -> str:
            return _cardinal(int(m.group(0).replace(",", "")), profile)

        text = _DATE_RE.sub(_date, text)
        text = _CURRENCY_RE.sub(_currency, text)
        text = _CURRENCY_SUFFIX_RE.sub(_currency_suffix, text)
        text = _PERCENT_RE.sub(_percent, text)
        text = _TIME_RE.sub(_time, text)
        text = _DECIMAL_RE.sub(_decimal, text)
        text = _LONG_DIGITS_RE.sub(_long, text)
        text = _INTEGER_RE.sub(_integer, text)
        return text

    def _currency_words(self, symbol, whole, frac, profile, original) -> str:
        """Shared currency renderer for both prefix (₹100) and suffix (100€)
        forms. Returns the original text if the symbol isn't mapped."""
        words = profile["currency"].get(symbol)
        if not words:
            return original
        major_word, minor_word = words
        whole_int = int(whole.replace(",", ""))
        out = f"{_cardinal(whole_int, profile)} {major_word}"
        if frac:
            minor_int = int(frac)
            if minor_int and minor_word:
                out += f" {profile['and']} {_cardinal(minor_int, profile)} {minor_word}"
        return out

    def _date_words(self, d: str, mth: str, yr: str, profile: dict) -> str:
        """'15/08/2025' -> '<fifteen> <August> <two thousand twenty-five>'.
        Falls back to a numeric month if no month table exists for the
        language; leaves impossible day/month combos as a plain read."""
        day, month, year = int(d), int(mth), int(yr)
        if not (1 <= day <= 31 and 1 <= month <= 12):
            return f"{d} {mth} {yr}"
        if len(yr) == 2:  # 2-digit year -> assume 2000s
            year += 2000
        months = _MONTHS.get(profile["num"])
        month_word = months[month - 1] if months else _cardinal(month, profile)
        return f"{_cardinal(day, profile)} {month_word} {_cardinal(year, profile)}"

    def _decimal_words(self, whole: str, frac: str, profile: dict) -> str:
        """'3.14' -> '<three> <point> <one> <four>'. If the language has no
        configured point word, leave the original decimal untouched."""
        point = profile.get("point")
        whole_words = _cardinal(int(whole.replace(",", "")), profile)
        if not point:
            return f"{whole}.{frac}"
        frac_words = _digit_by_digit(frac, profile)
        return f"{whole_words} {point} {frac_words}"

    def _time_words(self, hour: int, minute: int, ampm: str | None, profile: dict) -> str:
        """Speak a clock time naturally. Hindi and English get idiomatic
        templates; other languages get hour/minute cardinals (still far better
        than reading the colon)."""
        code = profile["num"]
        ap = (ampm or "").lower()

        if code == "hi":
            period = ""
            if ap == "am":
                period = "सुबह "
            elif ap == "pm":
                period = "शाम " if hour >= 5 else "दोपहर "
            if minute == 0:
                return f"{period}{_cardinal(hour, profile)} बजे"
            return f"{period}{_cardinal(hour, profile)} बजकर {_cardinal(minute, profile)} मिनट"

        if code == "en":
            period = ""
            if ap == "am":
                period = " in the morning"
            elif ap == "pm":
                period = " in the evening" if hour >= 5 else " in the afternoon"
            if minute == 0:
                return f"{_cardinal(hour, profile)} o'clock{period}"
            return f"{_cardinal(hour, profile)} {_cardinal(minute, profile)}{period}"

        # Generic: hour and minute cardinals.
        if minute == 0:
            return _cardinal(hour, profile)
        return f"{_cardinal(hour, profile)} {_cardinal(minute, profile)}"

    def _normalize_acronyms(self, text: str, base: str) -> str:
        letters = _LETTER_NAMES.get(base)

        def _spell(m: re.Match) -> str:
            word = m.group(1)
            # Only spell out curated acronyms (AI, OTP, URL...). Plain all-caps
            # words (STOP, NASA) are left for the engine to read as words.
            # We compare on the de-pluralized form so "PDFs" matches "PDF".
            key = word[:-1] if word.endswith("s") else word
            if word not in _SPELL_OUT_ACRONYMS and key not in _SPELL_OUT_ACRONYMS:
                return word
            if letters is not None:
                return " ".join(letters.get(ch, ch) for ch in word)
            # No script-specific letter names: only space out for Latin-script
            # languages so the engine reads the letters individually.
            if base in ("en", "fr", "de", "es"):
                return " ".join(word)
            return word

        return _ACRONYM_RE.sub(_spell, text)

    def _cleanup(self, result: str) -> str:
        # Whitespace
        result = _MULTI_NEWLINE_RE.sub(". ", result)
        result = _SINGLE_NEWLINE_RE.sub(" ", result)
        result = _MULTI_SPACE_RE.sub(" ", result)

        # Punctuation artifacts (preserve ! and ? for intonation)
        result = re.sub(r"\.{2,}", ".", result)
        result = re.sub(r",\s*\.", ".", result)
        result = re.sub(r"\.\s*,", ".", result)
        result = re.sub(r"^\s*[.,;:]\s*", "", result)
        result = re.sub(r"\s+([,.;:])", r"\1", result)
        result = re.sub(r"([,.;:])\s*([,.;:])", r"\1", result)
        result = re.sub(r"!{2,}", "!", result)
        result = re.sub(r"\?{2,}", "?", result)
        result = re.sub(r"([!?])([A-Za-z])", r"\1 \2", result)
        result = _MULTI_SPACE_RE.sub(" ", result)
        return result


# Singleton instance
voice_text_normalizer = VoiceTextNormalizer()
