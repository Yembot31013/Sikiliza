from __future__ import annotations

from collections.abc import AsyncIterator

from app.captions.context import format_context_block, normalize_language_tag
from app.captions.quality import is_usable_transcript
from app.captions.translate_parse import parse_translate_payload
from app.models import CaptionResult, Mode
from app.providers.base import SpeechProvider
from app.providers.http import (
    build_translate_user_prompt,
    extract_choice,
    extract_text,
    post_json,
    post_multipart,
)

GROQ_TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_TRANSLATE_URL = "https://api.groq.com/openai/v1/audio/translations"
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
WHISPER_MODEL = "whisper-large-v3"
DEFAULT_CHAT_MODEL = "openai/gpt-oss-20b"


class GroqProvider(SpeechProvider):
    name = "groq"

    def __init__(
        self,
        api_key: str,
        mode: Mode = "accurate",
        chat_model: str = DEFAULT_CHAT_MODEL,
        target_language: str = "en",
    ) -> None:
        super().__init__(mode)
        if not api_key:
            raise ValueError("GROQ_API_KEY is required for the Groq provider")
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self.chat_model = chat_model or DEFAULT_CHAT_MODEL
        self.target_language = target_language

    async def transcribe(self, wav_bytes: bytes) -> CaptionResult:
        if self.mode == "fast" and self.target_language == "en":
            english = extract_text(
                await post_multipart(
                    GROQ_TRANSLATE_URL,
                    headers=self._headers,
                    files=_wav_file(wav_bytes),
                    data={"model": WHISPER_MODEL, "response_format": "json"},
                )
            )
            if not english or not is_usable_transcript(english):
                return CaptionResult(source="", translation="")
            return CaptionResult(source="", translation=english, language="auto")

        source = extract_text(
            await post_multipart(
                GROQ_TRANSCRIBE_URL,
                headers=self._headers,
                files=_wav_file(wav_bytes),
                data={
                    "model": WHISPER_MODEL,
                    "response_format": "json",
                },
            )
        )
        if not source or not is_usable_transcript(source):
            return CaptionResult(source="", translation="")
        language, translation = await self._translate(source)
        return CaptionResult(source=source, translation=translation, language=language)

    async def caption_steps(self, wav_bytes: bytes) -> AsyncIterator[CaptionResult]:
        if self.mode == "fast" and self.target_language == "en":
            result = await self.transcribe(wav_bytes)
            if result.translation:
                yield result
            return

        source = extract_text(
            await post_multipart(
                GROQ_TRANSCRIBE_URL,
                headers=self._headers,
                files=_wav_file(wav_bytes),
                data={
                    "model": WHISPER_MODEL,
                    "response_format": "json",
                },
            )
        )
        if not source or not is_usable_transcript(source):
            return
        yield CaptionResult(source=source, translation="")
        language, translation = await self._translate(source)
        if not translation:
            return
        yield CaptionResult(source=source, translation=translation, language=language)

    async def _translate(self, source: str) -> tuple[str, str]:
        payload = await post_json(
            GROQ_CHAT_URL,
            headers=self._headers,
            payload={
                "model": self.chat_model,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "user",
                        "content": build_translate_user_prompt(
                            source,
                            target_language=self.target_language,
                            context_block=format_context_block(self._context_lines),
                        ),
                    },
                ],
            },
        )
        language, translation = parse_translate_payload(extract_choice(payload))
        if not translation:
            translation = extract_choice(payload).strip()
        return normalize_language_tag(language), translation


def _wav_file(wav_bytes: bytes) -> dict:
    return {"file": ("speech.wav", wav_bytes, "audio/wav")}
