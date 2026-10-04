from __future__ import annotations

from collections import Counter

# Neutral stream terms only — language-specific lists bias auto-detect too hard.
DEFAULT_SPEECH_BIAS = [
    "TikTok",
    "live",
    "gift",
    "host",
    "collab",
]

LANG_HINTS: dict[str, list[str]] = {
    "sw": ["sw-KE", "en-US"],
    "fr": ["fr-FR", "en-US"],
    "es": ["es-419", "en-US"],
    "pt": ["pt-BR", "en-US"],
    "de": ["de-DE", "en-US"],
    "en": ["en-US", "en-GB"],
    "it": ["it-IT", "en-US"],
    "ko": ["ko-KR", "en-US"],
    "zh": ["cmn-Hans-CN", "en-US"],
    "ar": ["ar-EG", "en-US"],
    "hi": ["hi-IN", "en-US"],
}


def normalize_language_tag(value: str) -> str:
    raw = value.strip().lower().replace("_", "-")
    if not raw:
        return ""
    primary = raw.split("-", 1)[0]
    aliases = {
        "fra": "fr",
        "fre": "fr",
        "spa": "es",
        "deu": "de",
        "ger": "de",
        "por": "pt",
        "swa": "sw",
        "eng": "en",
        "ita": "it",
        "kor": "ko",
        "cmn": "zh",
        "zho": "zh",
    }
    return aliases.get(primary, primary)


def format_context_block(
    lines: list[tuple[str, str]],
    *,
    limit: int = 4,
) -> str:
    recent = lines[-limit:]
    if not recent:
        return ""
    parts: list[str] = []
    for index, (source, translation) in enumerate(recent, start=1):
        src = source.strip() or "—"
        dst = translation.strip() or "—"
        parts.append(f"{index}. source: {src}\n   translation: {dst}")
    return "Recent captions (use for meaning/disambiguation):\n" + "\n".join(parts)


def locked_language_codes(votes: list[str], *, streak: int = 4) -> list[str]:
    """Optional STT hint after a long stable streak.

    Prefer leaving this unused for auto-detect — a wrong lock (e.g. SW on French
    speech) causes confident nonsense transcripts.
    """
    if len(votes) < streak:
        return []
    recent = [normalize_language_tag(item) for item in votes[-streak:]]
    if not recent or any(not item for item in recent):
        return []
    if len(set(recent)) != 1:
        return []
    return list(LANG_HINTS.get(recent[-1], []))


def dominant_language(votes: list[str]) -> str:
    cleaned = [normalize_language_tag(item) for item in votes if normalize_language_tag(item)]
    if not cleaned:
        return ""
    return Counter(cleaned).most_common(1)[0][0]
