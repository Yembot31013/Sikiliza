from app.config import Settings
from app.providers.factory import create_provider, is_configured, resolve_provider_name


def test_auto_prefers_gemini_when_key_present() -> None:
    settings = Settings(
        intron_api_key="intron_test",
        gemini_api_key="gemini_test",
        groq_api_key="gsk_test",
        provider="auto",
    )
    assert resolve_provider_name(settings) == "gemini"


def test_auto_prefers_intron_when_only_intron_present() -> None:
    settings = Settings(
        intron_api_key="intron_test",
        gemini_api_key="",
        groq_api_key="",
        openai_api_key="",
        provider="auto",
    )
    assert resolve_provider_name(settings) == "intron"


def test_auto_prefers_gemini_when_intron_missing() -> None:
    settings = Settings(
        intron_api_key="",
        gemini_api_key="gemini_test",
        groq_api_key="gsk_test",
        openai_api_key="sk_test",
        provider="auto",
    )
    assert resolve_provider_name(settings) == "gemini"


def test_auto_prefers_groq_when_gemini_missing() -> None:
    settings = Settings(
        intron_api_key="",
        gemini_api_key="",
        groq_api_key="gsk_test",
        openai_api_key="sk_test",
        provider="auto",
    )
    assert resolve_provider_name(settings) == "groq"


def test_auto_falls_back_to_openai() -> None:
    settings = Settings(
        intron_api_key="",
        gemini_api_key="",
        groq_api_key="",
        openai_api_key="sk_test",
        provider="auto",
    )
    assert resolve_provider_name(settings) == "openai"


def test_auto_falls_back_to_local_without_keys() -> None:
    settings = Settings(
        intron_api_key="",
        gemini_api_key="",
        groq_api_key="",
        openai_api_key="",
        provider="auto",
    )
    assert resolve_provider_name(settings) == "local"


def test_explicit_provider_wins() -> None:
    settings = Settings(
        intron_api_key="intron_test",
        gemini_api_key="gemini_test",
        groq_api_key="gsk_test",
        provider="openai",
        openai_api_key="sk_test",
    )
    assert resolve_provider_name(settings) == "openai"


def test_create_provider_builds_cloud_clients() -> None:
    intron = create_provider(Settings(intron_api_key="intron_test", provider="intron"))
    gemini = create_provider(Settings(gemini_api_key="gemini_test", provider="gemini"))
    groq = create_provider(Settings(groq_api_key="gsk_test", provider="groq"))
    openai = create_provider(Settings(openai_api_key="sk_test", provider="openai"))
    local = create_provider(Settings(provider="local"))
    assert intron.name == "intron"
    assert gemini.name == "gemini"
    assert groq.name == "groq"
    assert openai.name == "openai"
    assert local.name == "local"


def test_local_is_unconfigured_without_faster_whisper() -> None:
    settings = Settings(
        intron_api_key="",
        gemini_api_key="",
        groq_api_key="",
        openai_api_key="",
        provider="local",
    )
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        assert is_configured(settings) is False
    else:
        assert is_configured(settings) is True
