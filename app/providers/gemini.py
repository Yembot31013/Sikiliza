from __future__ import annotations

import base64
import logging
from collections.abc import AsyncIterator
from typing import Any, Mapping

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
    build_translate_user_prompt,
    extract_gemini_text,
    post_json,
)

logger = logging.getLogger(__name__)

GEMINI_GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)
TRANSCRIBE_MODEL = "gemini-3.5-transcribe"
CHAT_MODEL = "gemini-2.5-flash"


def _finish_reason(payload: Mapping[str, Any]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return ""
    first = candidates[0]
    if not isinstance(first, dict):
        return ""
    reason = first.get("finishReason")
    return reason if isinstance(reason, str) else ""


class GeminiProvider(SpeechProvider):
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        mode: Mode = "accurate",
        target_language: str = "en",
        transcribe_model: str = TRANSCRIBE_MODEL,
        chat_model: str = CHAT_MODEL,
    ) -> None:
        super().__init__(mode)
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for the Gemini provider")
        self._api_key = api_key
        self.target_language = target_language
        self.transcribe_model = transcribe_model
        self.chat_model = chat_model
        self._language_votes: list[str] = []

    async def transcribe(self, wav_bytes: bytes) -> CaptionResult:
        source = await self._transcribe_audio(wav_bytes)
        if not source or not is_usable_transcript(source):
            return CaptionResult(source="", translation="")
        language, translation = await self._translate(source)
        return CaptionResult(source=source, translation=translation, language=language)

    async def caption_steps(self, wav_bytes: bytes) -> AsyncIterator[CaptionResult]:
        source = await self._transcribe_audio(wav_bytes)
        if not source or not is_usable_transcript(source):
            return
        # Show source immediately; language comes only from translation detection.
        yield CaptionResult(source=source, translation="", language="")
        language, translation = await self._translate(source)
        if not translation:
            return
        yield CaptionResult(
            source=source,
            translation=translation,
            language=language,
        )

    async def _transcribe_audio(self, wav_bytes: bytes) -> str:
        # Always auto-detect. Locking STT to SW (etc.) after a few votes was
        # forcing French streams into Swahili hallucinations.
        audio_config: dict[str, Any] = {
            "mode": "SMART",
            "languageCodes": [],
            "customVocabulary": DEFAULT_SPEECH_BIAS,
        }

        payload = await post_json(
            GEMINI_GENERATE_URL.format(model=self.transcribe_model),
            headers={
                "x-goog-api-key": self._api_key,
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
                "generationConfig": {"audioTranscriptionConfig": audio_config},
            },
            timeout=18.0,
        )
        text = extract_gemini_text(payload)
        if not text:
            logger.debug(
                "Gemini transcribe returned no text (finish=%s)",
                _finish_reason(payload),
            )
        return text

    async def _translate(self, source: str) -> tuple[str, str]:
        context_block = format_context_block(self._context_lines)
        payload = await post_json(
            GEMINI_GENERATE_URL.format(model=self.chat_model),
            headers={
                "x-goog-api-key": self._api_key,
                "Content-Type": "application/json",
            },
            payload={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": build_translate_user_prompt(
                                    source,
                                    target_language=self.target_language,
                                    context_block=context_block,
                                )
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 280,
                    "responseMimeType": "application/json",
                },
            },
            timeout=12.0,
        )
        language, translation = parse_translate_payload(extract_gemini_text(payload))
        language = normalize_language_tag(language)
        if not translation.strip() and is_usable_transcript(source):
            # Second pass: models sometimes empty-out slang; force a translation.
            retry = await post_json(
                GEMINI_GENERATE_URL.format(model=self.chat_model),
                headers={
                    "x-goog-api-key": self._api_key,
                    "Content-Type": "application/json",
                },
                payload={
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": (
                                        f"Translate to {self.target_language}. "
                                        "Return ONLY JSON "
                                        '{"language":"<iso639-1>","translation":"<text>"}. '
                                        f"Transcript:\n{source.strip()}"
                                    )
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0,
                        "maxOutputTokens": 280,
                        "responseMimeType": "application/json",
                    },
                },
                timeout=12.0,
            )
            language, translation = parse_translate_payload(extract_gemini_text(retry))
            language = normalize_language_tag(language)
        if language:
            self._language_votes = [*self._language_votes[-5:], language]
        return language, translation
