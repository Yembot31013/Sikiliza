from __future__ import annotations

from app.config import Settings
from app.models import ProviderName
from app.providers.base import SpeechProvider
from app.providers.gemini import GeminiProvider
from app.providers.groq import GroqProvider
from app.providers.intron import IntronProvider
from app.providers.local_whisper import LocalWhisperProvider
from app.providers.openai import OpenAIProvider


def resolve_provider_name(settings: Settings) -> ProviderName:
    if settings.provider != "auto":
        return settings.provider
    # Gemini first: stable auto language + translate. Intron is opt-in
    # (SIKILIZA_PROVIDER=intron) until its streaming gateway is reliable.
    if settings.gemini_api_key:
        return "gemini"
    if settings.groq_api_key:
        return "groq"
    if settings.openai_api_key:
        return "openai"
    if settings.intron_api_key:
        return "intron"
    return "local"


def is_configured(settings: Settings) -> bool:
    name = resolve_provider_name(settings)
    if name == "intron":
        return bool(settings.intron_api_key)
    if name == "gemini":
        return bool(settings.gemini_api_key)
    if name == "groq":
        return bool(settings.groq_api_key)
    if name == "openai":
        return bool(settings.openai_api_key)
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


def create_provider(
    settings: Settings,
    *,
    target_language: str | None = None,
) -> SpeechProvider:
    name = resolve_provider_name(settings)
    target = target_language or settings.target_language
    if name == "intron":
        return IntronProvider(
            settings.intron_api_key,
            mode=settings.mode,
            source_language=settings.intron_source_lang,
            target_language=target,
            gemini_api_key=settings.gemini_api_key,
            groq_api_key=settings.groq_api_key,
            openai_api_key=settings.openai_api_key,
            gemini_chat_model=settings.gemini_chat_model,
            groq_chat_model=settings.groq_chat_model,
        )
    if name == "gemini":
        return GeminiProvider(
            settings.gemini_api_key,
            mode=settings.mode,
            target_language=target,
            transcribe_model=settings.gemini_transcribe_model,
            chat_model=settings.gemini_chat_model,
        )
    if name == "groq":
        return GroqProvider(
            settings.groq_api_key,
            mode=settings.mode,
            chat_model=settings.groq_chat_model,
            target_language=target,
        )
    if name == "openai":
        return OpenAIProvider(
            settings.openai_api_key,
            mode=settings.mode,
            target_language=target,
        )
    return LocalWhisperProvider(model_size=settings.whisper_model, mode=settings.mode)
