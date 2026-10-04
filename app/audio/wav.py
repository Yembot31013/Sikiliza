from __future__ import annotations

import struct
import wave
from io import BytesIO

SAMPLE_RATE = 16_000
CHANNELS = 1
SAMPLE_WIDTH = 2


def build_wav(pcm: bytes, sample_rate: int = SAMPLE_RATE) -> bytes:
    if len(pcm) % 2 != 0:
        raise ValueError("PCM16 data length must be even")

    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(SAMPLE_WIDTH)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)

    payload = buffer.getvalue()
    if payload[20:22] != struct.pack("<H", 1):
        raise RuntimeError("WAV encoder produced a non-PCM format")
    return payload
