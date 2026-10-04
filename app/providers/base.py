from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.models import CaptionResult, Mode


class SpeechProvider(ABC):
    name: str

    def __init__(self, mode: Mode = "accurate") -> None:
        self.mode = mode
        self._context_lines: list[tuple[str, str]] = []
        self._language_hint = ""

    @abstractmethod
    async def transcribe(self, wav_bytes: bytes) -> CaptionResult:
        raise NotImplementedError

    def set_context(
        self,
        lines: list[tuple[str, str]],
        *,
        language_hint: str = "",
    ) -> None:
        self._context_lines = list(lines[-6:])
        self._language_hint = language_hint.strip().lower()

    async def caption_steps(self, wav_bytes: bytes) -> AsyncIterator[CaptionResult]:
        """Yield one or more caption results for a single audio window.

        Default: a single final result. Providers may yield a provisional STT
        result first, then a translated update, so the UI feels faster.
        """
        result = await self.transcribe(wav_bytes)
        yield result
