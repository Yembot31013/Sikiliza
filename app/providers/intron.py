from __future__ import annotations

import asyncio
import base64
import json
import logging
import wave
from collections.abc import AsyncIterator, Callable
from io import BytesIO
from typing import Any
from urllib.parse import urlencode

import websockets

from app.captions.context import (
    DEFAULT_SPEECH_BIAS,
    format_context_block,
    normalize_language_tag,
)
from app.captions.quality import is_usable_transcript
from app.captions.translate_parse import parse_translate_payload
from app.models import CaptionResult, Mode
from app.providers.base import SpeechProvider
from app.providers.http import (
    ProviderError,
    build_translate_user_prompt,
    extract_choice,
    extract_gemini_text,
    post_json,
)

logger = logging.getLogger(__name__)

INTRON_STREAM_URL = "wss://infer.voice.intron.io/stt/v1/stream"
GEMINI_GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"

# Intron requires an ASR language code. `sw` is Swahili-English code-switched.
# https://docs.voice.intron.io/docs/stt/supported-languages
INTRON_LANGUAGES = {
    "sw",
    "en",
    "fr",
    "es",
    "pt",
    "de",
    "ha",
    "yo",
    "ig",
    "pcm",
    "rw",
    "zu",
    "af",
    "am",
    "ar",
}

MIN_CHUNK = 1024
MAX_CHUNK = 16 * 1024

ConnectFn = Callable[..., Any]


def _default_connect(url: str, **kwargs: Any) -> Any:
    # Intron's gateway mis-handles permessage-deflate; RSV bits then trip
    # "protocol error: reserved bits must be 0".
    kwargs.setdefault("compression", None)
    kwargs.setdefault("open_timeout", 12)
    kwargs.setdefault("close_timeout", 8)
    kwargs.setdefault("max_size", 2**22)
    kwargs.setdefault("ping_interval", 20)
    kwargs.setdefault("ping_timeout", 20)
    return websockets.connect(url, **kwargs)


def _format_ws_error(exc: BaseException) -> str:
    code = getattr(exc, "code", None)
    reason = getattr(exc, "reason", None)
    detail = str(exc).strip() or reason or type(exc).__name__
    if code is not None:
        reason_text = str(reason or detail).strip()
        return f"{type(exc).__name__} code={code} {reason_text}".strip()
    return f"{type(exc).__name__}: {detail}"


class IntronProvider(SpeechProvider):
    """Intron streaming STT + cloud chat translation.

    Strong for African languages / Swahili-English code-switching via
    https://docs.voice.intron.io/docs/stt/streaming
    """

    name = "intron"

    def __init__(
        self,
        api_key: str,
        *,
        mode: Mode = "accurate",
        source_language: str = "sw",
        target_language: str = "en",
        gemini_api_key: str = "",
        groq_api_key: str = "",
        openai_api_key: str = "",
        gemini_chat_model: str = "gemini-2.5-flash",
        groq_chat_model: str = "openai/gpt-oss-20b",
        connect: ConnectFn | None = None,
    ) -> None:
        super().__init__(mode)
        if not api_key:
            raise ValueError("INTRON_API_KEY is required for the Intron provider")
        self._api_key = api_key
        self.source_language = normalize_language_tag(source_language) or "sw"
        self.target_language = target_language
        self._gemini_api_key = gemini_api_key
        self._groq_api_key = groq_api_key
        self._openai_api_key = openai_api_key
        self._gemini_chat_model = gemini_chat_model
        self._groq_chat_model = groq_chat_model
        self._connect = connect or _default_connect

    async def transcribe(self, wav_bytes: bytes) -> CaptionResult:
        source = await self._transcribe_audio(wav_bytes)
        if not source or not is_usable_transcript(source):
            return CaptionResult(source="", translation="")
        language, translation = await self._translate(source)
        return CaptionResult(
            source=source,
            translation=translation or source,
            language=language or self._asr_language(),
        )

    async def caption_steps(self, wav_bytes: bytes) -> AsyncIterator[CaptionResult]:
        source = await self._transcribe_audio(wav_bytes)
        if not source or not is_usable_transcript(source):
            return
        asr_lang = self._asr_language()
        yield CaptionResult(source=source, translation="", language=asr_lang)
        language, translation = await self._translate(source)
        if not translation:
            return
        yield CaptionResult(
            source=source,
            translation=translation,
            language=language or asr_lang,
        )

    def _asr_language(self) -> str:
        hint = normalize_language_tag(self._language_hint)
        if hint in INTRON_LANGUAGES:
            return hint
        if self.source_language in INTRON_LANGUAGES:
            return self.source_language
        return "sw"

    async def _transcribe_audio(self, wav_bytes: bytes) -> str:
        try:
            return await self._intron_stream(wav_bytes)
        except ProviderError as exc:
            detail = str(exc)
            if not self._can_fallback(detail):
                raise
            logger.warning(
                "Intron unavailable (%s); falling back to Gemini STT",
                detail,
            )
            try:
                # Empty transcript is a valid miss — do not re-raise Intron.
                return await self._gemini_stt(wav_bytes)
            except ProviderError as fallback_exc:
                logger.warning("Gemini STT fallback failed: %s", fallback_exc)
                raise fallback_exc from exc

    def _can_fallback(self, detail: str) -> bool:
        if not self._gemini_api_key:
            return False
        lowered = detail.lower()
        return any(
            token in lowered
            for token in (
                "resource_exhausted",
                "capacity",
                "quota_exceeded",
                "protocol error",
                "1002",
                "connectionclosed",
            )
        )

    async def _intron_stream(self, wav_bytes: bytes) -> str:
        pcm = _pcm_from_wav(wav_bytes)
        if len(pcm) < MIN_CHUNK:
            # Pad tiny windows so Intron accepts the chunk.
            pcm = pcm + b"\x00" * (MIN_CHUNK - len(pcm))

        language = self._asr_language()
        query = urlencode(
            {
                "sample_rate": "16000",
                "bit_rate": "16",
                "num_channels": "1",
                "use_language_asr_input": language,
            }
        )
        url = f"{INTRON_STREAM_URL}?{query}"
        headers = {"Authorization": f"Bearer {self._api_key}"}

        try:
            async with self._connect(
                url,
                additional_headers=headers,
            ) as socket:
                return await _run_intron_session(socket, pcm)
        except ProviderError:
            raise
        except Exception as exc:
            detail = _format_ws_error(exc)
            logger.warning("Intron stream failed: %s", detail)
            raise ProviderError(f"Intron STT failed: {detail}") from exc

    async def _gemini_stt(self, wav_bytes: bytes) -> str:
        payload = await post_json(
            GEMINI_GENERATE_URL.format(model="gemini-3.5-transcribe"),
            headers={
                "x-goog-api-key": self._gemini_api_key,
                "Content-Type": "application/json",
            },
            payload={
                "contents": [
                    {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "audio/wav",
                                    "data": base64.b64encode(wav_bytes).decode("ascii"),
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "audioTranscriptionConfig": {
                        "languageCodes": [],
                        "mode": "SMART",
                        "customVocabulary": DEFAULT_SPEECH_BIAS,
                    }
                },
            },
            timeout=18.0,
        )
        return extract_gemini_text(payload)

    async def _translate(self, source: str) -> tuple[str, str]:
        prompt = build_translate_user_prompt(
            source,
            target_language=self.target_language,
            context_block=format_context_block(self._context_lines),
        )
        if self._gemini_api_key:
            return await self._translate_gemini(prompt)
        if self._groq_api_key:
            return await self._translate_openai_compatible(
                GROQ_CHAT_URL,
                self._groq_api_key,
                self._groq_chat_model,
                prompt,
            )
        if self._openai_api_key:
            return await self._translate_openai_compatible(
                OPENAI_CHAT_URL,
                self._openai_api_key,
                "gpt-4o-mini",
                prompt,
            )
        # No chat key — return source as-is (still useful Swahili captions).
        return self._asr_language(), source

    async def _translate_gemini(self, prompt: str) -> tuple[str, str]:
        payload = await post_json(
            GEMINI_GENERATE_URL.format(model=self._gemini_chat_model),
            headers={
                "x-goog-api-key": self._gemini_api_key,
                "Content-Type": "application/json",
            },
            payload={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 280,
                    "responseMimeType": "application/json",
                },
            },
            timeout=12.0,
        )
        language, translation = parse_translate_payload(extract_gemini_text(payload))
        return normalize_language_tag(language), translation

    async def _translate_openai_compatible(
        self,
        url: str,
        api_key: str,
        model: str,
        prompt: str,
    ) -> tuple[str, str]:
        payload = await post_json(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            payload={
                "model": model,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=12.0,
        )
        language, translation = parse_translate_payload(extract_choice(payload))
        if not translation:
            translation = extract_choice(payload).strip()
        return normalize_language_tag(language), translation


async def _run_intron_session(socket: Any, pcm: bytes) -> str:
    final_text = ""
    partial_text = ""
    ack_id = 0
    pending: list[dict[str, Any]] = []

    async def next_message(*, timeout: float) -> dict[str, Any]:
        if pending:
            return pending.pop(0)
        return await _recv_json(socket, timeout=timeout)

    # Wait for SESSION_CREATED (or fail fast on auth errors).
    created = await next_message(timeout=12.0)
    message_type = str(created.get("message_type") or "")
    if message_type in {
        "AUTHENTICATION_ERROR",
        "QUOTA_EXCEEDED",
        "RESOURCE_EXHAUSTED",
        "ERROR",
    }:
        raise ProviderError(
            f"Intron {message_type}: {created.get('message') or created.get('status') or 'failed'}"
        )
    if message_type != "SESSION_CREATED":
        logger.debug("Intron first message was %s: %s", message_type, created)

    for chunk in _iter_pcm_chunks(pcm):
        ack_id += 1
        await socket.send(
            json.dumps(
                {
                    "message_type": "INPUT_AUDIO_CHUNK",
                    "audio_base_64": base64.b64encode(chunk).decode("ascii"),
                    "ack_id": ack_id,
                }
            )
        )
        partial = await _drain_partials(next_message, pending, idle_timeout=0.05)
        if partial:
            partial_text = partial

    await socket.send(json.dumps({"message_type": "COMMIT"}))

    deadline = asyncio.get_running_loop().time() + 20.0
    while asyncio.get_running_loop().time() < deadline:
        payload = await next_message(
            timeout=max(0.1, deadline - asyncio.get_running_loop().time()),
        )
        kind = str(payload.get("message_type") or "")
        if kind == "PARTIAL_TRANSCRIPT":
            text = str(payload.get("transcript") or "").strip()
            if text:
                partial_text = text
            continue
        if kind == "COMMITTED_TRANSCRIPT":
            final_text = str(
                payload.get("transcript_text") or payload.get("transcript") or ""
            ).strip()
            break
        if kind in {
            "ERROR",
            "INPUT_ERROR",
            "AUTHENTICATION_ERROR",
            "QUOTA_EXCEEDED",
            "SESSION_TIME_LIMIT_EXCEEDED",
            "INSUFFICIENT_AUDIO_ACTIVITY",
        }:
            raise ProviderError(
                f"Intron {kind}: {payload.get('message') or 'stream error'}"
            )

    return final_text or partial_text


async def _drain_partials(
    next_message: Any,
    pending: list[dict[str, Any]],
    *,
    idle_timeout: float,
) -> str:
    latest = ""
    try:
        while True:
            payload = await next_message(timeout=idle_timeout)
            kind = str(payload.get("message_type") or "")
            if kind == "AUDIO_CHUNK_ACK":
                continue
            if kind == "PARTIAL_TRANSCRIPT":
                text = str(payload.get("transcript") or "").strip()
                if text:
                    latest = text
                continue
            if kind in {
                "ERROR",
                "INPUT_ERROR",
                "AUTHENTICATION_ERROR",
                "QUOTA_EXCEEDED",
            }:
                raise ProviderError(
                    f"Intron {kind}: {payload.get('message') or 'stream error'}"
                )
            # COMMITTED or anything else — keep for the main loop.
            pending.append(payload)
            return latest
    except TimeoutError:
        return latest


async def _recv_json(socket: Any, *, timeout: float) -> dict[str, Any]:
    raw = await asyncio.wait_for(socket.recv(), timeout=timeout)
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ProviderError("Intron returned a malformed payload")
    return payload


def _iter_pcm_chunks(pcm: bytes) -> list[bytes]:
    if not pcm:
        return [b"\x00" * MIN_CHUNK]
    chunks: list[bytes] = []
    for index in range(0, len(pcm), MAX_CHUNK):
        chunks.append(pcm[index : index + MAX_CHUNK])
    if len(chunks[-1]) < MIN_CHUNK:
        if len(chunks) == 1:
            chunks[0] = chunks[0] + b"\x00" * (MIN_CHUNK - len(chunks[0]))
        else:
            chunks[-2] = chunks[-2] + chunks[-1]
            chunks.pop()
    return chunks


def _pcm_from_wav(wav_bytes: bytes) -> bytes:
    with wave.open(BytesIO(wav_bytes), "rb") as wav_file:
        return wav_file.readframes(wav_file.getnframes())
