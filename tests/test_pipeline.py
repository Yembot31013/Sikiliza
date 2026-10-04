import pytest

from app.models import CaptionResult
from app.pipeline import LivePipeline
from app.providers.base import SpeechProvider


class FakeProvider(SpeechProvider):
    name = "fake"

    def __init__(self) -> None:
        self.calls: list[bytes] = []

    async def transcribe(self, wav_bytes: bytes) -> CaptionResult:
        self.calls.append(wav_bytes)
        return CaptionResult(source="Habari", translation="Hello")


class EmptyProvider(SpeechProvider):
    name = "empty"

    async def transcribe(self, wav_bytes: bytes) -> CaptionResult:
        return CaptionResult(source="", translation="")


class BoomProvider(SpeechProvider):
    name = "boom"

    async def transcribe(self, wav_bytes: bytes) -> CaptionResult:
        raise RuntimeError("upstream timeout")


@pytest.mark.asyncio
async def test_pipeline_emits_final_caption_for_speech() -> None:
    from app.audio.synth import silence, tone

    provider = FakeProvider()
    pipeline = LivePipeline(provider=provider, mode="accurate")
    events = []

    for chunk in (tone(900, amplitude=0.3), silence(800)):
        events.extend(await pipeline.ingest(chunk))

    finals = [event for event in events if event["type"] == "final"]
    assert len(finals) == 1
    assert finals[0]["source"] == "Habari"
    assert finals[0]["translation"] == "Hello"
    assert provider.calls
    assert any(
        event["type"] == "status" and event.get("processing") is True for event in events
    )


@pytest.mark.asyncio
async def test_pipeline_marks_processing_before_provider_returns() -> None:
    from app.audio.synth import silence, tone

    class SlowProvider(SpeechProvider):
        name = "slow"

        async def transcribe(self, wav_bytes: bytes) -> CaptionResult:
            return CaptionResult(source="Sasa", translation="Now")

    pipeline = LivePipeline(provider=SlowProvider(), mode="accurate")
    events = []
    for chunk in (tone(900, amplitude=0.3), silence(800)):
        events.extend(await pipeline.ingest(chunk))

    status_events = [event for event in events if event["type"] == "status"]
    processing_events = [event for event in status_events if event.get("processing") is True]
    assert processing_events
    assert processing_events[0]["speaking"] is False
    assert status_events[-1]["processing"] is False


@pytest.mark.asyncio
async def test_pipeline_skips_empty_transcripts() -> None:
    from app.audio.synth import silence, tone

    pipeline = LivePipeline(provider=EmptyProvider(), mode="accurate")
    events = []
    for chunk in (tone(900, amplitude=0.3), silence(800)):
        events.extend(await pipeline.ingest(chunk))
    assert [event["type"] for event in events if event["type"] == "final"] == []


@pytest.mark.asyncio
async def test_pipeline_reports_provider_errors_without_dying() -> None:
    from app.audio.synth import silence, tone

    pipeline = LivePipeline(provider=BoomProvider(), mode="accurate")
    events = []
    for chunk in (tone(900, amplitude=0.3), silence(800)):
        events.extend(await pipeline.ingest(chunk))

    errors = [event for event in events if event["type"] == "error"]
    assert len(errors) == 1
    assert errors[0]["code"] == "TRANSCRIBE_FAILED"
    assert errors[0]["soft"] is True
    events.extend(await pipeline.ingest(tone(900, amplitude=0.3) + silence(800)))
    assert any(event["type"] == "error" for event in events)


@pytest.mark.asyncio
async def test_pipeline_emits_provisional_then_translation() -> None:
    from app.audio.synth import silence, tone

    class StepProvider(SpeechProvider):
        name = "steps"

        async def transcribe(self, wav_bytes: bytes):
            return CaptionResult(source="Habari", translation="Hello")

        async def caption_steps(self, wav_bytes: bytes):
            yield CaptionResult(source="Habari", translation="")
            yield CaptionResult(source="Habari", translation="Hello")

    pipeline = LivePipeline(provider=StepProvider(), mode="accurate")
    events = []
    for chunk in (tone(900, amplitude=0.3), silence(800)):
        events.extend(await pipeline.ingest(chunk))

    finals = [event for event in events if event["type"] == "final"]
    assert len(finals) == 2
    assert finals[0]["kind"] == "new"
    assert finals[0]["translation"] == ""
    assert finals[1]["kind"] == "update"
    assert finals[1]["translation"] == "Hello"
    assert finals[0]["id"] == finals[1]["id"]


@pytest.mark.asyncio
async def test_pipeline_keeps_provisional_when_translate_fails() -> None:
    from app.audio.synth import silence, tone
    from app.providers.http import ProviderError

    class PartialProvider(SpeechProvider):
        name = "partial"

        async def transcribe(self, wav_bytes: bytes):
            return CaptionResult(source="Habari", translation="")

        async def caption_steps(self, wav_bytes: bytes):
            yield CaptionResult(source="Habari", translation="", language="sw")
            raise ProviderError("translate timeout")

    pipeline = LivePipeline(provider=PartialProvider(), mode="accurate")
    events = []
    for chunk in (tone(900, amplitude=0.3), silence(800)):
        events.extend(await pipeline.ingest(chunk))

    finals = [event for event in events if event["type"] == "final"]
    errors = [event for event in events if event["type"] == "error"]
    assert len(finals) == 1
    assert finals[0]["source"] == "Habari"
    assert len(errors) == 1
    assert errors[0]["soft"] is True
