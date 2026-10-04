from __future__ import annotations

import base64
import json
import wave
from io import BytesIO

import pytest

from app.audio.wav import build_wav
from app.providers.intron import IntronProvider, _iter_pcm_chunks, _pcm_from_wav


def _tiny_wav(ms: int = 800) -> bytes:
    samples = int(16_000 * (ms / 1000))
    pcm = b"\x00\x10" * samples
    return build_wav(pcm)


class FakeSocket:
    def __init__(self, inbound: list[dict]) -> None:
        self._inbound = [json.dumps(item) for item in inbound]
        self.sent: list[dict] = []

    async def __aenter__(self) -> "FakeSocket":
        return self

    async def __aexit__(self, *args: object) -> bool:
        return False

    async def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))

    async def recv(self) -> str:
        if not self._inbound:
            raise TimeoutError("no more messages")
        return self._inbound.pop(0)


@pytest.mark.asyncio
async def test_intron_streams_pcm_and_returns_committed_transcript(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wav = _tiny_wav(900)
    pcm = _pcm_from_wav(wav)
    fake = FakeSocket(
        [
            {
                "message_type": "SESSION_CREATED",
                "session_id": "abc",
                "configs": {"use_language_asr_input": "sw"},
            },
            *[{"message_type": "AUDIO_CHUNK_ACK", "chunk_id": i} for i in range(1, 8)],
            {
                "message_type": "COMMITTED_TRANSCRIPT",
                "transcript_text": "Habari yenu wasee",
            },
        ]
    )

    def fake_connect(*args: object, **kwargs: object) -> FakeSocket:
        return fake

    async def fake_translate(self: IntronProvider, source: str) -> tuple[str, str]:
        assert source == "Habari yenu wasee"
        return "sw", "Hello everyone"

    monkeypatch.setattr(
        "app.providers.intron.IntronProvider._translate",
        fake_translate,
    )

    provider = IntronProvider(
        "intron_test",
        source_language="sw",
        gemini_api_key="gemini_test",
        connect=fake_connect,
    )
    result = await provider.transcribe(wav)
    assert result.source == "Habari yenu wasee"
    assert result.translation == "Hello everyone"
    assert result.language == "sw"

    assert fake.sent[0]["message_type"] == "INPUT_AUDIO_CHUNK"
    assert fake.sent[0]["ack_id"] == 1
    decoded = base64.b64decode(fake.sent[0]["audio_base_64"])
    assert len(decoded) >= 1024
    assert fake.sent[-1] == {"message_type": "COMMIT"}
    assert sum(len(_pcm_from_wav(wav)[i : i + 16 * 1024]) for i in range(0, len(pcm), 16 * 1024)) >= len(pcm) - 16 * 1024


@pytest.mark.asyncio
async def test_intron_caption_steps_are_provisional_then_translated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeSocket(
        [
            {"message_type": "SESSION_CREATED", "session_id": "abc"},
            {
                "message_type": "COMMITTED_TRANSCRIPT",
                "transcript_text": "Sasa tutaenda sokoni",
            },
        ]
    )

    def fake_connect(*args: object, **kwargs: object) -> FakeSocket:
        return fake

    async def fake_translate(self: IntronProvider, source: str) -> tuple[str, str]:
        return "sw", "Now we will go to the market"

    monkeypatch.setattr("app.providers.intron.IntronProvider._translate", fake_translate)
    provider = IntronProvider("intron_test", connect=fake_connect)
    steps = [step async for step in provider.caption_steps(_tiny_wav())]
    assert len(steps) == 2
    assert steps[0].source == "Sasa tutaenda sokoni"
    assert steps[0].translation == ""
    assert steps[0].language == "sw"
    assert steps[1].translation == "Now we will go to the market"


def test_pcm_chunking_respects_intron_minimum() -> None:
    chunks = _iter_pcm_chunks(b"\x01\x02")
    assert len(chunks) == 1
    assert len(chunks[0]) >= 1024


def test_pcm_from_wav_roundtrip() -> None:
    wav = _tiny_wav(100)
    pcm = _pcm_from_wav(wav)
    assert len(pcm) > 0
    with wave.open(BytesIO(wav), "rb") as handle:
        assert handle.getframerate() == 16000


def test_format_ws_error_includes_close_code() -> None:
    from app.providers.intron import _format_ws_error

    class Closed(Exception):
        code = 1002
        reason = "reserved bits must be 0"

    assert "1002" in _format_ws_error(Closed())
    assert "reserved bits" in _format_ws_error(Closed())


@pytest.mark.asyncio
async def test_intron_falls_back_to_gemini_on_capacity_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.providers.http import ProviderError

    class Boom:
        async def __aenter__(self) -> "Boom":
            raise ProviderError("Intron RESOURCE_EXHAUSTED: CAPACITY_NOT_AVAILABLE")

        async def __aexit__(self, *args: object) -> bool:
            return False

    def fake_connect(*args: object, **kwargs: object) -> Boom:
        return Boom()

    async def fake_gemini_stt(self: IntronProvider, wav_bytes: bytes) -> str:
        assert wav_bytes
        return "Habari za jioni"

    async def fake_translate(self: IntronProvider, source: str) -> tuple[str, str]:
        return "sw", "Good evening"

    monkeypatch.setattr(IntronProvider, "_gemini_stt", fake_gemini_stt)
    monkeypatch.setattr(IntronProvider, "_translate", fake_translate)

    provider = IntronProvider(
        "intron_test",
        gemini_api_key="gemini_test",
        connect=fake_connect,
    )
    result = await provider.transcribe(_tiny_wav())
    assert result.source == "Habari za jioni"
    assert result.translation == "Good evening"


@pytest.mark.asyncio
async def test_intron_empty_gemini_fallback_does_not_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.providers.http import ProviderError

    class Boom:
        async def __aenter__(self) -> "Boom":
            raise ProviderError(
                "Intron STT failed: ConnectionClosedError code=1006 "
                "sent 1002 (protocol error)"
            )

        async def __aexit__(self, *args: object) -> bool:
            return False

    def fake_connect(*args: object, **kwargs: object) -> Boom:
        return Boom()

    async def fake_gemini_stt(self: IntronProvider, wav_bytes: bytes) -> str:
        return ""

    monkeypatch.setattr(IntronProvider, "_gemini_stt", fake_gemini_stt)
    provider = IntronProvider(
        "intron_test",
        gemini_api_key="gemini_test",
        connect=fake_connect,
    )
    result = await provider.transcribe(_tiny_wav())
    assert result.source == ""
    assert result.translation == ""


def test_can_fallback_matches_capacity_and_protocol() -> None:
    provider = IntronProvider("intron_test", gemini_api_key="gemini_test")
    assert provider._can_fallback("Intron RESOURCE_EXHAUSTED: CAPACITY_NOT_AVAILABLE")
    assert provider._can_fallback("Intron STT failed: 1002 protocol error")
    assert not IntronProvider("intron_test")._can_fallback(
        "Intron RESOURCE_EXHAUSTED: CAPACITY_NOT_AVAILABLE"
    )
