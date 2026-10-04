from __future__ import annotations

import math
from array import array

from app.audio.wav import SAMPLE_RATE


def silence(duration_ms: int, sample_rate: int = SAMPLE_RATE) -> bytes:
    count = _sample_count(duration_ms, sample_rate)
    return array("h", [0] * count).tobytes()


def tone(
    duration_ms: int,
    hz: float = 220.0,
    amplitude: float = 0.2,
    sample_rate: int = SAMPLE_RATE,
) -> bytes:
    count = _sample_count(duration_ms, sample_rate)
    peak = int(max(0.0, min(amplitude, 1.0)) * 32767)
    samples = [
        int(peak * math.sin(2 * math.pi * hz * index / sample_rate))
        for index in range(count)
    ]
    return array("h", samples).tobytes()


def _sample_count(duration_ms: int, sample_rate: int) -> int:
    if duration_ms < 0:
        raise ValueError("duration_ms must be >= 0")
    return int(sample_rate * duration_ms / 1000)
