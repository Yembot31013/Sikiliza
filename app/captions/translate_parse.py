from __future__ import annotations

import json
import re

_CODE_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
_JSON_OBJECT = re.compile(r"\{[\s\S]*\}")
_LANG_FIELD = re.compile(r'"language"\s*:\s*"([^"]*)"', re.IGNORECASE)
_TRANS_FIELD = re.compile(
    r'"translation"\s*:\s*"((?:\\.|[^"\\])*)"',
    re.IGNORECASE,
)
_JSON_LEAK = re.compile(
    r'(```|^\s*\{|\{\s*$|"language"\s*:|"translation"\s*:|'
    r"here is the json|json requested|responseMimeType|"
    r"compact json|only json)",
    re.IGNORECASE | re.MULTILINE,
)
_TRAILING_JUNK = re.compile(r"[\s`]*\{+\s*$")


def parse_translate_payload(text: str) -> tuple[str, str]:
    """Return (language, translation) from model JSON.

    Never returns prose/markdown/JSON scaffolding as a caption.
    """
    cleaned = text.strip()
    if not cleaned:
        return "", ""

    fenced = _CODE_FENCE.search(cleaned)
    if fenced:
        cleaned = fenced.group(1).strip()

    parsed = _try_load_json(cleaned)
    if parsed is None:
        match = _JSON_OBJECT.search(cleaned)
        if match:
            parsed = _try_load_json(match.group(0))

    if isinstance(parsed, dict):
        language = parsed.get("language")
        translation = parsed.get("translation")
        lang = language.strip() if isinstance(language, str) else ""
        text_out = translation.strip() if isinstance(translation, str) else ""
        return lang, sanitize_caption_text(text_out)

    # Partial JSON (stream cut off) — pull fields if present.
    lang_match = _LANG_FIELD.search(cleaned)
    trans_match = _TRANS_FIELD.search(cleaned)
    if lang_match or trans_match:
        lang = lang_match.group(1).strip() if lang_match else ""
        text_out = _unescape_json_string(trans_match.group(1)) if trans_match else ""
        return lang, sanitize_caption_text(text_out)

    # Plain speech fallback only when it does not look like JSON/tooling leakage.
    if looks_like_json_leak(cleaned):
        return "", ""
    return "", sanitize_caption_text(cleaned)


def sanitize_caption_text(text: str) -> str:
    value = text.strip().strip("`").strip()
    value = _TRAILING_JUNK.sub("", value).strip()
    value = re.sub(
        r"^Here is the JSON requested:\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = value.strip().strip("`").strip()
    if looks_like_json_leak(value):
        return ""
    return value


def looks_like_json_leak(text: str) -> bool:
    raw = text.strip()
    if not raw:
        return False
    if _JSON_LEAK.search(raw):
        return True
    if raw.count("{") != raw.count("}"):
        return True
    return False


def _unescape_json_string(value: str) -> str:
    try:
        loaded = json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return value.replace('\\"', '"').replace("\\n", "\n")
    return loaded if isinstance(loaded, str) else value


def _try_load_json(text: str) -> object | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
