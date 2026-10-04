from __future__ import annotations

from app.models import CaptionResult, Mode
from app.providers.base import SpeechProvider
from app.providers.http import (
    extract_choice,
    extract_text,
    post_json,
    post_multipart,
    translate_system_prompt,
)

OPENAI_TRANSCRIBE_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_TRANSLATE_URL = "https://api.openai.com/v1/audio/translations"
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
WHISPER_MODEL = "whisper-1"
CHAT_MODEL = "gpt-4o-mini"


class OpenAIProvider(SpeechProvider):
    name = "openai"

    def __init__(
        self,
        api_key: str,
        mode: Mode = "accurate",
        target_language: str = "en",
    ) -> None:
        super().__init__(mode)
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for the OpenAI provider")
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self.target_language = target_language

    async def transcribe(self, wav_bytes: bytes) -> CaptionResult:
        if self.mode == "fast" and self.target_language == "en":
            english = extract_text(
                await post_multipart(
                    OPENAI_TRANSLATE_URL,
                    headers=self._headers,
                    files=_wav_file(wav_bytes),
                    data={"model": WHISPER_MODEL, "response_format": "json"},
                )
            )
            return CaptionResult(source="", translation=english)

        source = extract_text(
            await post_multipart(
                OPENAI_TRANSCRIBE_URL,
                headers=self._headers,
                files=_wav_file(wav_bytes),
                data={
                    "model": WHISPER_MODEL,
                    "response_format": "json",
                },
            )
        )
        if not source:
            return CaptionResult(source="", translation="")
        translation = await self._translate(source)
        return CaptionResult(source=source, translation=translation)

    async def _translate(self, source: str) -> str:
        payload = await post_json(
            OPENAI_CHAT_URL,
            headers=self._headers,
            payload={
                "model": CHAT_MODEL,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "system",
                        "content": translate_system_prompt(self.target_language),
                    },
                    {"role": "user", "content": source},
                ],
            },
        )
        return extract_choice(payload)


def _wav_file(wav_bytes: bytes) -> dict:
    return {"file": ("speech.wav", wav_bytes, "audio/wav")}
