from app.audio.wav import build_wav, SAMPLE_RATE


def test_wav_header_is_canonical_pcm16() -> None:
    pcm = bytes([0, 0, 1, 0, 2, 0, 3, 0])
    wav = build_wav(pcm)

    assert wav[:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"
    assert wav[12:16] == b"fmt "
    assert wav[20:22] == (1).to_bytes(2, "little")
    assert wav[22:24] == (1).to_bytes(2, "little")
    assert wav[24:28] == SAMPLE_RATE.to_bytes(4, "little")
    assert wav[36:40] == b"data"
    assert wav[40:44] == len(pcm).to_bytes(4, "little")
    assert wav[44:] == pcm
    assert len(wav) == 44 + len(pcm)


def test_wav_rejects_odd_length_pcm() -> None:
    try:
        build_wav(b"\x00")
    except ValueError as exc:
        assert "even" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")
