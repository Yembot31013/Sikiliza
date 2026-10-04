from app.audio.synth import silence, tone
from app.audio.vad import pcm16_rms, is_speech


def test_silence_is_below_speech_threshold() -> None:
    assert pcm16_rms(silence(200)) < 0.001
    assert is_speech(silence(200)) is False


def test_tone_is_detected_as_speech() -> None:
    speech = tone(200, amplitude=0.25)
    assert pcm16_rms(speech) > 0.1
    assert is_speech(speech) is True


def test_empty_audio_is_not_speech() -> None:
    assert pcm16_rms(b"") == 0.0
    assert is_speech(b"") is False
