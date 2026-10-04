import pytest

from app.providers.gemini import GeminiProvider
from app.providers.groq import GroqProvider
from app.providers.openai import OpenAIProvider


@pytest.mark.asyncio
async def test_groq_accurate_transcribes_then_translates(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_multipart(url: str, **kwargs: object) -> dict:
        assert "transcriptions" in url
        assert "language" not in kwargs.get("data", {})
        return {"text": "Habari yenu"}

    async def fake_json(url: str, **kwargs: object) -> dict:
        assert "chat" in url
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"language":"sw","translation":"Hello everyone"}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.providers.groq.post_multipart", fake_multipart)
    monkeypatch.setattr("app.providers.groq.post_json", fake_json)
    result = await GroqProvider("gsk_test", mode="accurate").transcribe(b"RIFF")
    assert result.source == "Habari yenu"
    assert result.translation == "Hello everyone"
    assert result.language == "sw"


@pytest.mark.asyncio
async def test_groq_fast_uses_translation_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_multipart(url: str, **kwargs: object) -> dict:
        assert "translations" in url
        return {"text": "Hello there"}

    monkeypatch.setattr("app.providers.groq.post_multipart", fake_multipart)
    result = await GroqProvider("gsk_test", mode="fast").transcribe(b"RIFF")
    assert result.translation == "Hello there"
    assert result.source == ""


@pytest.mark.asyncio
async def test_openai_accurate_transcribes_then_translates(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_multipart(url: str, **kwargs: object) -> dict:
        return {"text": "Asante"}

    async def fake_json(url: str, **kwargs: object) -> dict:
        return {"choices": [{"message": {"content": "Thank you"}}]}

    monkeypatch.setattr("app.providers.openai.post_multipart", fake_multipart)
    monkeypatch.setattr("app.providers.openai.post_json", fake_json)
    result = await OpenAIProvider("sk_test", mode="accurate").transcribe(b"RIFF")
    assert result.source == "Asante"
    assert result.translation == "Thank you"


@pytest.mark.asyncio
async def test_gemini_transcribes_with_auto_language(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    async def fake_json(url: str, **kwargs: object) -> dict:
        payload = kwargs.get("payload")
        assert isinstance(payload, dict)
        calls.append({"url": url, "payload": payload})
        if "gemini-3.5-transcribe" in url:
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "audioTranscription": {
                                        "text": "Habari yenu"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '{"language":"sw","translation":"Hello everyone"}'
                            }
                        ]
                    }
                }
            ]
        }

    monkeypatch.setattr("app.providers.gemini.post_json", fake_json)
    result = await GeminiProvider("gemini_test", mode="accurate").transcribe(b"RIFFWAVE")
    assert result.source == "Habari yenu"
    assert result.translation == "Hello everyone"
    assert result.language == "sw"
    assert calls[0]["payload"]["generationConfig"]["audioTranscriptionConfig"]["languageCodes"] == []
    assert "customVocabulary" in calls[0]["payload"]["generationConfig"]["audioTranscriptionConfig"]


@pytest.mark.asyncio
async def test_gemini_caption_steps_are_provisional_then_final(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_json(url: str, **kwargs: object) -> dict:
        if "gemini-3.5-transcribe" in url:
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"audioTranscription": {"text": "Habari yenu"}}]
                        }
                    }
                ]
            }
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": '{"language":"sw","translation":"Hello"}'}]
                    }
                }
            ]
        }

    monkeypatch.setattr("app.providers.gemini.post_json", fake_json)
    steps = [
        result
        async for result in GeminiProvider("gemini_test").caption_steps(b"RIFFWAVE")
    ]
    assert len(steps) == 2
    assert steps[0].source == "Habari yenu"
    assert steps[0].translation == ""
    assert steps[1].translation == "Hello"
    assert steps[1].language == "sw"


@pytest.mark.asyncio
async def test_gemini_retries_empty_translation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    async def fake_json(url: str, **kwargs: object) -> dict:
        calls.append(url)
        if "gemini-3.5-transcribe" in url:
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "audioTranscription": {
                                        "text": "Wachanganye wewe baba"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        if len([c for c in calls if "gemini-2.5-flash" in c]) == 1:
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": '{"language":"sw","translation":""}'}]
                        }
                    }
                ]
            }
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    '{"language":"sw",'
                                    '"translation":"You people mess around dad"}'
                                )
                            }
                        ]
                    }
                }
            ]
        }

    monkeypatch.setattr("app.providers.gemini.post_json", fake_json)
    result = await GeminiProvider("gemini_test").transcribe(b"RIFFWAVE")
    assert result.translation == "You people mess around dad"
    assert sum(1 for c in calls if "gemini-2.5-flash" in c) == 2


@pytest.mark.asyncio
async def test_gemini_drops_unusable_noise(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_json(url: str, **kwargs: object) -> dict:
        return {
            "candidates": [
                {"content": {"parts": [{"audioTranscription": {"text": "49yyu"}}]}}
            ]
        }

    monkeypatch.setattr("app.providers.gemini.post_json", fake_json)
    steps = [
        result
        async for result in GeminiProvider("gemini_test").caption_steps(b"RIFFWAVE")
    ]
    assert steps == []
