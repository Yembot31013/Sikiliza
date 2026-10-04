from __future__ import annotations

import re

_LETTER_RE = re.compile(r"[^\W\d_]", re.UNICODE)
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def is_usable_transcript(text: str) -> bool:
    """Reject noise/hallucination fragments that should never become captions."""
    raw = text.strip()
    if not raw:
        return False

    compact = re.sub(r"\s+", "", raw)
    if len(compact) < 3:
        return False

    letters = _LETTER_RE.findall(raw)
    if len(letters) < 3:
        return False

    letter_ratio = len(letters) / max(len(compact), 1)
    if letter_ratio < 0.45:
        return False

    # Pure digits / timestamps / prices alone.
    if re.fullmatch(r"[\d\s.:/-]+", raw):
        return False

    # Alphanumeric mash like "49yyu" / "3x7kq".
    alnum = re.sub(r"[^\w]", "", compact, flags=re.UNICODE)
    digits = sum(1 for ch in alnum if ch.isdigit())
    if digits >= 2 and len(alnum) <= 8:
        return False

    words = _WORD_RE.findall(raw)
    if not words:
        return False

    # Model/tooling leakage that must never become a caption.
    lowered = raw.lower()
    if "```" in raw or '"language"' in lowered or '"translation"' in lowered:
        return False
    if "json requested" in lowered or "here is the json" in lowered:
        return False
    if raw.count("{") != raw.count("}"):
        return False

    # Single gibberish token like "asdfgh".
    if len(words) == 1:
        token = words[0]
        if len(token) <= 2:
            return False
        if _looks_like_gibberish(token):
            return False

    return True


def _looks_like_gibberish(token: str) -> bool:
    lower = token.lower()
    vowels = sum(1 for ch in lower if ch in "aeiouàáâãäåèéêëìíîïòóôõöùúûüy")
    if len(lower) >= 4 and vowels == 0:
        return True
    return False
