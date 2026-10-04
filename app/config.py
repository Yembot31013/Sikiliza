from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.models import Mode, ProviderName


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "Sikiliza"
    intron_api_key: str = Field(default="", validation_alias="INTRON_API_KEY")
    intron_source_lang: str = Field(default="sw", validation_alias="INTRON_SOURCE_LANG")
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    groq_api_key: str = ""
    openai_api_key: str = ""
    mode: Mode = Field(default="accurate", validation_alias="SIKILIZA_MODE")
    provider: ProviderName = Field(default="auto", validation_alias="SIKILIZA_PROVIDER")
    target_language: str = Field(default="en", validation_alias="SIKILIZA_TARGET_LANG")
    whisper_model: str = Field(default="small", validation_alias="WHISPER_MODEL")
    groq_chat_model: str = Field(
        default="openai/gpt-oss-20b",
        validation_alias="GROQ_CHAT_MODEL",
    )
    gemini_transcribe_model: str = Field(
        default="gemini-3.5-transcribe",
        validation_alias="GEMINI_TRANSCRIBE_MODEL",
    )
    gemini_chat_model: str = Field(
        default="gemini-2.5-flash",
        validation_alias="GEMINI_CHAT_MODEL",
    )
    host: str = Field(default="127.0.0.1", validation_alias="SIKILIZA_HOST")
    port: int = Field(default=8765, validation_alias="SIKILIZA_PORT")
    allowed_origins: list[str] = [
        "http://127.0.0.1:5273",
        "http://localhost:5273",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


def get_settings() -> Settings:
    return Settings()
