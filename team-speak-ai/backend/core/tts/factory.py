from enum import Enum
from core.tts.base import BaseTTS
from core.tts.edge_tts import EdgeTTS
from core.tts.minimax_tts import MiniMaxTTS


class TTSProvider(Enum):
    EDGE = "edge"
    MINIMAX = "minimax"


def create_tts(provider: TTSProvider, config: dict) -> BaseTTS:
    if provider == TTSProvider.EDGE:
        return EdgeTTS(**config)
    elif provider == TTSProvider.MINIMAX:
        return MiniMaxTTS(**config)
    raise ValueError(f"Unknown TTS provider: {provider}")
