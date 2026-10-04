from dataclasses import dataclass, field
from typing import Literal


Mode = Literal["accurate", "fast"]
ProviderName = Literal["auto", "intron", "gemini", "groq", "openai", "local"]
SourceName = Literal["tab", "mic"]
EventType = Literal["ready", "status", "partial", "final", "error"]


@dataclass(frozen=True)
class CaptionResult:
    source: str
    translation: str
    language: str = ""


@dataclass(frozen=True)
class AudioWindow:
    pcm: bytes
    start_ms: int
    end_ms: int
    rms: float

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


@dataclass
class SessionState:
    source: SourceName = "tab"
    mode: Mode = "accurate"
    listening: bool = False
    speaking: bool = False
    captions: list[dict] = field(default_factory=list)
