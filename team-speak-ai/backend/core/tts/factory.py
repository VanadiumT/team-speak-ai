from enum import Enum
from core.tts.base import BaseTTS
from core.tts.edge_tts import EdgeTTS


class TTSProvider(Enum):
    EDGE = "edge"


def create_tts(provider: TTSProvider, config: dict) -> BaseTTS:
    if provider == TTSProvider.EDGE:
        return EdgeTTS(**config)
    raise ValueError(f"Unknown TTS provider: {provider}")
