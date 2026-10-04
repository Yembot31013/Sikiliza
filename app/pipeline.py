from __future__ import annotations

import logging
from typing import Any

from app.audio.buffer import AudioBuffer
from app.audio.wav import build_wav
from app.captions.context import dominant_language
from app.captions.merge import merge_caption
from app.captions.quality import is_usable_transcript
from app.captions.translate_parse import sanitize_caption_text
from app.models import AudioWindow, CaptionResult, Mode
from app.providers.base import SpeechProvider
from app.providers.http import ProviderError

logger = logging.getLogger(__name__)


class LivePipeline:
    def __init__(self, provider: SpeechProvider, mode: Mode = "accurate") -> None:
        self.provider = provider
        self.mode = mode
        # Slightly stricter VAD cuts music/noise “speech” that becomes garbage text.
        self.buffer = AudioBuffer(
            min_speech_ms=550,
            max_utterance_ms=3000,
            silence_flush_ms=400,
            min_rms=0.02,
        )
        self._last_source = ""
        self._seq = 0
        self._speaking = False
        self._context: list[tuple[str, str]] = []
        self._languages: list[str] = []

    def feed(self, pcm_chunk: bytes) -> tuple[list[dict[str, Any]], list[AudioWindow]]:
        """Run VAD only. Never awaits the provider — safe for the WS receive loop."""
        events: list[dict[str, Any]] = []
        windows = self.buffer.ingest(pcm_chunk)

        if windows:
            if self._speaking:
                self._speaking = False
                events.append(_status(speaking=False, processing=False))
            return events, windows

        speaking_now = self.buffer.in_speech
        if speaking_now != self._speaking:
            self._speaking = speaking_now
            events.append(_status(speaking=speaking_now, processing=False))
        return events, []

    async def ingest(self, pcm_chunk: bytes) -> list[dict[str, Any]]:
        """Test/helper path: feed + process windows inline."""
        events, windows = self.feed(pcm_chunk)
        if not windows:
            return events

        out = list(events)
        out.append(_status(speaking=False, processing=True))
        for window in windows:
            out.extend(await self.process_window(window))
        speaking_now = self.buffer.in_speech
        self._speaking = speaking_now
        out.append(_status(speaking=speaking_now, processing=False))
        return out

    async def flush(self) -> list[dict[str, Any]]:
        window = self.buffer.flush()
        if window is None:
            return []
        events = [_status(speaking=False, processing=True)]
        events.extend(await self.process_window(window))
        self._speaking = False
        events.append(_status(speaking=False, processing=False))
        return events

    @property
    def in_speech(self) -> bool:
        return self.buffer.in_speech

    @property
    def detected_language(self) -> str:
        return dominant_language(self._languages)

    async def process_window(self, window: AudioWindow) -> list[dict[str, Any]]:
        self.provider.set_context(
            self._context,
            language_hint=self.detected_language,
        )
        wav_bytes = build_wav(window.pcm)
        events: list[dict[str, Any]] = []
        try:
            async for result in self.provider.caption_steps(wav_bytes):
                events.extend(self._finalize(result, window))
            return events
        except ProviderError as exc:
            logger.warning("Transcription failed: %s", exc)
            # Keep any provisional caption already finalized for this window.
            events.append(
                _soft_error(str(exc) or "Could not reach speech API. Still listening.")
            )
            return events
        except Exception:
            logger.exception("Transcription failed")
            events.append(
                _soft_error("Could not transcribe that moment. Still listening.")
            )
            return events

    def _finalize(self, result: CaptionResult, window: AudioWindow) -> list[dict[str, Any]]:
        source = sanitize_caption_text(result.source)
        translation = sanitize_caption_text(result.translation)
        if not source and not translation:
            return []
        if source and not is_usable_transcript(source):
            return []

        result = CaptionResult(
            source=source,
            translation=translation,
            language=(result.language or "").strip(),
        )

        fingerprint = result.source or result.translation
        language = result.language

        # Same utterance again (provisional STT → translated/corrected update).
        if self._seq > 0 and fingerprint == self._last_source:
            event = {
                "type": "final",
                "id": self._seq,
                "kind": "update",
                "source": result.source,
                "translation": result.translation,
                "language": language,
                "startMs": window.start_ms,
                "endMs": window.end_ms,
                "revised": bool(result.translation.strip()),
            }
            self._remember(result)
            return [event]

        decision = merge_caption(self._last_source, fingerprint)
        if decision.kind == "skip":
            return []

        if decision.kind == "new":
            self._seq += 1
        self._last_source = fingerprint
        event = {
            "type": "final",
            "id": self._seq,
            "kind": decision.kind,
            "source": result.source,
            "translation": result.translation,
            "language": language,
            "startMs": window.start_ms,
            "endMs": window.end_ms,
            "revised": decision.kind == "update" and bool(result.translation.strip()),
        }
        self._remember(result)
        return [event]

    def _remember(self, result: CaptionResult) -> None:
        source = result.source.strip()
        translation = result.translation.strip()
        if not source and not translation:
            return
        if translation:
            # Replace last context row when this is a correction of the same source.
            if self._context and self._context[-1][0] == source:
                self._context[-1] = (source, translation)
            else:
                self._context = [*self._context[-5:], (source, translation)]
        if result.language.strip():
            self._languages = [*self._languages[-8:], result.language.strip()]


def _status(*, speaking: bool, processing: bool) -> dict[str, Any]:
    return {"type": "status", "speaking": speaking, "processing": processing}


def _soft_error(message: str) -> dict[str, Any]:
    return {
        "type": "error",
        "code": "TRANSCRIBE_FAILED",
        "soft": True,
        "message": message,
    }


def _has_text(result: CaptionResult) -> bool:
    return bool(result.translation.strip() or result.source.strip())
