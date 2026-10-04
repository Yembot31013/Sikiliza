from __future__ import annotations

import asyncio
import logging
import tempfile
from functools import lru_cache

from app.models import CaptionResult, Mode
from app.providers.base import SpeechProvider

logger = logging.getLogger(__name__)


class LocalWhisperProvider(SpeechProvider):
    name = "local"

    def __init__(self, model_size: str = "small", mode: Mode = "accurate") -> None:
        super().__init__(mode)
        self.model_size = model_size

    async def transcribe(self, wav_bytes: bytes) -> CaptionResult:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run, wav_bytes)

    def _run(self, wav_bytes: bytes) -> CaptionResult:
        model = _load_model(self.model_size)
        translation = _decode(model, wav_bytes, task="translate", language=None)
        if self.mode == "fast":
            return CaptionResult(source="", translation=translation)
        source = _decode(model, wav_bytes, task="transcribe", language=None)
        return CaptionResult(source=source, translation=translation)


@lru_cache(maxsize=1)
def _load_model(model_size: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "Local Whisper is not installed. Run: pip install -e '.[local]' "
            "or set INTRON_API_KEY / GEMINI_API_KEY / GROQ_API_KEY / OPENAI_API_KEY in .env"
        ) from exc
    logger.info("Loading local Whisper model '%s' on CPU", model_size)
    return WhisperModel(model_size, device="cpu", compute_type="int8")


def _decode(model, wav_bytes: bytes, task: str, language: str | None) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav") as handle:
        handle.write(wav_bytes)
        handle.flush()
        segments, _info = model.transcribe(
            handle.name,
            language=language,
            task=task,
            vad_filter=True,
            beam_size=1,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()
