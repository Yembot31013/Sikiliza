from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TARGET_LANGUAGE_NAMES = {
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "sw": "Swahili",
    "de": "German",
    "pt": "Portuguese",
}

_client: httpx.AsyncClient | None = None
_DEFAULT_TIMEOUT = httpx.Timeout(20.0, connect=5.0)


def translate_system_prompt(target_language: str = "en") -> str:
    target = TARGET_LANGUAGE_NAMES.get(target_language, "English")
    return (
        "You caption a live stream in realtime. Translate the spoken transcript into "
        f"natural spoken {target}. "
        "Use recent captions as context to resolve slang, nicknames, Sheng, code-switching, "
        "and words with multiple meanings. Prefer the meaning that fits the ongoing conversation. "
        "Keep names, nicknames, numbers, and trending/local slang when they matter. "
        "Do not invent content that was not spoken. "
        f"If the text is already {target}, keep it natural and unchanged in meaning "
        "(copy the transcript into translation). "
        "Always fill translation for real speech — including slang, Sheng, mixed languages, "
        "and short utterances. Only leave translation as an empty string when the transcript "
        "has no meaningful words at all (pure noise / music-only). "
        "Output rules (strict): return ONE JSON object only. "
        "No markdown. No code fences. No preamble. No explanation. "
        'Exact shape: {"language":"<iso639-1 of the CURRENT transcript only>",'
        '"translation":"<text>"}. '
        "Detect language from this transcript itself — do not reuse a previous "
        "language guess if this line is clearly different."
    )


def build_translate_user_prompt(
    source: str,
    *,
    target_language: str = "en",
    context_block: str = "",
) -> str:
    parts = [translate_system_prompt(target_language)]
    if context_block.strip():
        parts.append(context_block.strip())
    parts.append(f"Current transcript:\n{source.strip()}")
    return "\n\n".join(parts)


# Back-compat alias used by older imports/tests.
TRANSLATE_SYSTEM = translate_system_prompt("en")


class ProviderError(RuntimeError):
    """Transient or upstream provider failure. Safe to keep the live session open."""


def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=_DEFAULT_TIMEOUT,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _client


async def close_http_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


async def post_multipart(
    url: str,
    *,
    headers: Mapping[str, str],
    files: dict[str, Any],
    data: dict[str, str],
    timeout: float | None = None,
) -> dict[str, Any]:
    client = get_http_client()
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = await client.post(
                url,
                headers=headers,
                files=files,
                data=data,
                timeout=timeout,
            )
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                await _backoff(attempt)
                continue
            if response.status_code >= 400:
                raise ProviderError(_http_error(response))
            payload = response.json()
            if not isinstance(payload, dict):
                raise ProviderError("Provider returned a malformed payload")
            return payload
        except ProviderError:
            raise
        except httpx.HTTPError as exc:
            last_error = exc
            logger.warning("HTTP attempt %s failed: %s", attempt + 1, exc)
            if attempt == 2:
                break
            await _backoff(attempt)
    raise ProviderError(_unreachable_message(last_error)) from last_error


async def post_json(
    url: str,
    *,
    headers: Mapping[str, str],
    payload: dict[str, Any],
    timeout: float | None = None,
) -> dict[str, Any]:
    client = get_http_client()
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                await _backoff(attempt)
                continue
            if response.status_code >= 400:
                raise ProviderError(_http_error(response))
            body = response.json()
            if not isinstance(body, dict):
                raise ProviderError("Provider returned a malformed payload")
            return body
        except ProviderError:
            raise
        except httpx.HTTPError as exc:
            last_error = exc
            logger.warning("JSON attempt %s failed: %s", attempt + 1, exc)
            if attempt == 2:
                break
            await _backoff(attempt)
    raise ProviderError(_unreachable_message(last_error)) from last_error


def extract_text(payload: Mapping[str, Any]) -> str:
    text = payload.get("text")
    if not isinstance(text, str):
        return ""
    return text.strip()


def extract_choice(payload: Mapping[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return content.strip() if isinstance(content, str) else ""


def extract_gemini_text(payload: Mapping[str, Any]) -> str:
    """Pull transcript/text from a Gemini generateContent payload.

    Gemini chat models return ``parts[].text``. Gemini 3.5 Transcribe returns
    ``parts[].audioTranscription.text`` (and optionally word annotations).
    """
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return ""
    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""
    chunks: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            chunks.append(text.strip())
            continue
        transcription = part.get("audioTranscription")
        if not isinstance(transcription, dict):
            continue
        transcript = transcription.get("text")
        if isinstance(transcript, str) and transcript.strip():
            chunks.append(transcript.strip())
            continue
        words = transcription.get("words")
        if isinstance(words, list):
            word_chunks = [
                word.get("word").strip()
                for word in words
                if isinstance(word, dict)
                and isinstance(word.get("word"), str)
                and word["word"].strip()
            ]
            if word_chunks:
                chunks.append(" ".join(word_chunks))
    return " ".join(chunks).strip()


def _http_error(response: httpx.Response) -> str:
    detail = response.text.strip().replace("\n", " ")
    return f"Provider HTTP {response.status_code}: {detail[:240]}"


def _unreachable_message(exc: Exception | None) -> str:
    detail = str(exc or "")
    if "name resolution" in detail.lower() or "Errno -3" in detail:
        return "Speech API DNS/network blip. Still listening."
    if "timed out" in detail.lower() or "Timeout" in detail:
        return "Speech API timed out. Still listening."
    return "Speech API is unreachable. Still listening."


async def _backoff(attempt: int) -> None:
    await asyncio.sleep(0.25 * (2**attempt))
