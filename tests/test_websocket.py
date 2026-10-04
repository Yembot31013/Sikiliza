from fastapi.testclient import TestClient

from app.audio.synth import silence, tone
from app.main import create_app
from app.models import CaptionResult
from app.providers.base import SpeechProvider


class FakeProvider(SpeechProvider):
    name = "fake"

    async def transcribe(self, wav_bytes: bytes) -> CaptionResult:
        return CaptionResult(source="Habari", translation="Hello")


def test_websocket_rejects_unconfigured_provider(monkeypatch) -> None:
    monkeypatch.setattr("app.routers.stream.is_configured", lambda _settings: False)
    client = TestClient(create_app())
    with client.websocket_connect("/ws") as socket:
        payload = socket.receive_json()
        assert payload["type"] == "error"
        assert payload["code"] == "NOT_CONFIGURED"


def test_websocket_emits_ready_and_caption(monkeypatch) -> None:
    monkeypatch.setattr("app.routers.stream.is_configured", lambda _settings: True)
    monkeypatch.setattr("app.routers.stream.create_provider", lambda _settings, **kwargs: FakeProvider())
    monkeypatch.setattr("app.routers.stream.resolve_provider_name", lambda _settings: "gemini")
    client = TestClient(create_app())
    with client.websocket_connect("/ws") as socket:
        ready = socket.receive_json()
        assert ready["type"] == "ready"
        assert ready["provider"] == "gemini"
        socket.send_bytes(tone(900, amplitude=0.3) + silence(800))
        event = socket.receive_json()
        if event.get("type") != "final":
            event = socket.receive_json()
        assert event["type"] == "final"
        assert event["translation"] == "Hello"
        socket.send_text('{"type":"stop"}')
