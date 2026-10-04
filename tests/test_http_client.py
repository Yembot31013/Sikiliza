import pytest

from app.providers.http import ProviderError, close_http_client, post_json, post_multipart


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text or str(payload)

    def json(self) -> dict:
        return self._payload


class FakeClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self._responses = list(responses)

    async def post(self, *args: object, **kwargs: object) -> FakeResponse:
        return self._responses.pop(0)


@pytest.fixture(autouse=True)
async def _reset_http_client():
    await close_http_client()
    yield
    await close_http_client()


@pytest.mark.asyncio
async def test_post_multipart_returns_json(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient([FakeResponse(200, {"text": "Habari"})])
    monkeypatch.setattr("app.providers.http.get_http_client", lambda: client)
    payload = await post_multipart(
        "https://example.test",
        headers={},
        files={"file": ("speech.wav", b"data", "audio/wav")},
        data={"model": "whisper-large-v3"},
    )
    assert payload["text"] == "Habari"


@pytest.mark.asyncio
async def test_post_json_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient(
        [
            FakeResponse(503, text="busy"),
            FakeResponse(200, {"choices": [{"message": {"content": "Hello"}}]}),
        ]
    )
    monkeypatch.setattr("app.providers.http.get_http_client", lambda: client)
    monkeypatch.setattr("app.providers.http._backoff", _no_sleep)
    payload = await post_json("https://example.test", headers={}, payload={})
    assert payload["choices"][0]["message"]["content"] == "Hello"


@pytest.mark.asyncio
async def test_post_json_surfaces_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient([FakeResponse(400, text="bad key")])
    monkeypatch.setattr("app.providers.http.get_http_client", lambda: client)
    with pytest.raises(ProviderError, match="400"):
        await post_json("https://example.test", headers={}, payload={})


async def _no_sleep(_attempt: int) -> None:
    return None
