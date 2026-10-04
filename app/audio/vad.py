from __future__ import annotations

import math
from array import array

DEFAULT_MIN_RMS = 0.02


def pcm16_rms(pcm: bytes) -> float:
    samples = _as_samples(pcm)
    if not samples:
        return 0.0
    mean_square = sum(sample * sample for sample in samples) / len(samples)
    return math.sqrt(mean_square) / 32768.0


def is_speech(pcm: bytes, min_rms: float = DEFAULT_MIN_RMS) -> bool:
    return pcm16_rms(pcm) >= min_rms


def _as_samples(pcm: bytes) -> array:
    samples = array("h")
    usable = pcm[: len(pcm) - (len(pcm) % 2)]
    if usable:
        samples.frombytes(usable)
    return samples
