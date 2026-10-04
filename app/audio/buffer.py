from __future__ import annotations

from app.audio.vad import pcm16_rms
from app.audio.wav import SAMPLE_RATE
from app.models import AudioWindow

BYTES_PER_SAMPLE = 2


class AudioBuffer:
    """Collect PCM16 into utterance windows using energy VAD."""

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        min_speech_ms: int = 700,
        max_utterance_ms: int = 5500,
        silence_flush_ms: int = 650,
        min_rms: float = 0.02,
        frame_ms: int = 30,
    ) -> None:
        self.sample_rate = sample_rate
        self.min_speech_ms = min_speech_ms
        self.max_utterance_ms = max_utterance_ms
        self.silence_flush_ms = silence_flush_ms
        self.min_rms = min_rms
        self.frame_bytes = int(sample_rate * frame_ms / 1000) * BYTES_PER_SAMPLE
        self._pending = bytearray()
        self._utterance = bytearray()
        self._cursor_ms = 0
        self._utterance_start_ms = 0
        self._speech_ms = 0
        self._silence_ms = 0
        self._in_speech = False

    @property
    def in_speech(self) -> bool:
        return self._in_speech

    def ingest(self, pcm_chunk: bytes) -> list[AudioWindow]:
        if len(pcm_chunk) % 2 == 1:
            pcm_chunk = pcm_chunk[:-1]
        self._pending.extend(pcm_chunk)
        emitted: list[AudioWindow] = []

        while len(self._pending) >= self.frame_bytes:
            frame = bytes(self._pending[: self.frame_bytes])
            del self._pending[: self.frame_bytes]
            window = self._consume_frame(frame)
            if window is not None:
                emitted.append(window)

        return emitted

    def flush(self) -> AudioWindow | None:
        if self._in_speech and self._speech_ms >= self.min_speech_ms:
            return self._emit()
        self._reset_utterance()
        return None

    def _consume_frame(self, frame: bytes) -> AudioWindow | None:
        frame_ms = self._bytes_to_ms(len(frame))
        speaking = pcm16_rms(frame) >= self.min_rms

        if speaking:
            if not self._in_speech:
                self._in_speech = True
                self._utterance_start_ms = self._cursor_ms
                self._speech_ms = 0
                self._silence_ms = 0
                self._utterance = bytearray()
            self._utterance.extend(frame)
            self._speech_ms += frame_ms
            self._silence_ms = 0
            self._cursor_ms += frame_ms
            if self._speech_ms >= self.max_utterance_ms:
                return self._emit()
            return None

        self._cursor_ms += frame_ms
        if not self._in_speech:
            return None

        self._utterance.extend(frame)
        self._silence_ms += frame_ms
        if self._silence_ms >= self.silence_flush_ms:
            if self._speech_ms >= self.min_speech_ms:
                return self._emit()
            self._reset_utterance()
        return None

    def _emit(self) -> AudioWindow:
        pcm = bytes(self._utterance)
        window = AudioWindow(
            pcm=pcm,
            start_ms=self._utterance_start_ms,
            end_ms=self._utterance_start_ms + self._bytes_to_ms(len(pcm)),
            rms=pcm16_rms(pcm),
        )
        self._reset_utterance()
        return window

    def _reset_utterance(self) -> None:
        self._utterance = bytearray()
        self._speech_ms = 0
        self._silence_ms = 0
        self._in_speech = False

    def _bytes_to_ms(self, size: int) -> int:
        return int(size / (self.sample_rate * BYTES_PER_SAMPLE) * 1000)
