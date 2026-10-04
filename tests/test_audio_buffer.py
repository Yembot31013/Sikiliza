from app.audio.buffer import AudioBuffer
from app.audio.synth import silence, tone


def make_buffer() -> AudioBuffer:
    return AudioBuffer(
        sample_rate=16000,
        min_speech_ms=400,
        max_utterance_ms=2000,
        silence_flush_ms=300,
        min_rms=0.02,
    )


def test_silence_does_not_emit_a_window() -> None:
    buffer = make_buffer()
    windows = buffer.ingest(silence(800))
    assert windows == []


def test_speech_then_silence_emits_one_utterance() -> None:
    buffer = make_buffer()
    windows = buffer.ingest(tone(500, amplitude=0.3))
    assert windows == []

    windows = buffer.ingest(silence(400))
    assert len(windows) == 1
    assert windows[0].duration_ms >= 400
    assert windows[0].rms > 0.02


def test_long_speech_flushes_at_max_utterance() -> None:
    buffer = make_buffer()
    windows = buffer.ingest(tone(2200, amplitude=0.3))
    assert len(windows) == 1
    assert 1900 <= windows[0].duration_ms <= 2200


def test_short_blip_is_ignored() -> None:
    buffer = make_buffer()
    windows = buffer.ingest(tone(120, amplitude=0.3) + silence(400))
    assert windows == []


def test_flush_emits_open_utterance() -> None:
    buffer = make_buffer()
    assert buffer.ingest(tone(500, amplitude=0.3)) == []
    flushed = buffer.flush()
    assert flushed is not None
    assert flushed.duration_ms >= 400


def test_odd_length_chunk_is_trimmed() -> None:
    buffer = make_buffer()
    windows = buffer.ingest(tone(500, amplitude=0.3) + b"\x00" + silence(400))
    assert len(windows) == 1


def test_two_utterances_emit_separately() -> None:
    buffer = make_buffer()
    first = buffer.ingest(tone(500, amplitude=0.3) + silence(400))
    second = buffer.ingest(tone(500, amplitude=0.3) + silence(400))
    assert len(first) == 1
    assert len(second) == 1
    assert second[0].start_ms > first[0].end_ms
