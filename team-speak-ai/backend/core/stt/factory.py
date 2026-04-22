from enum import Enum
from core.stt.base import BaseSTT
from core.stt.whisper_stt import WhisperSTT
from core.stt.minimax_stt import MiniMaxSTT
from core.stt.sensevoice_stt import SenseVoiceSTT


class STTProvider(Enum):
    WHISPER = "whisper"
    MINIMAX = "minimax"
    SENSEVOICE = "sensevoice"


def create_stt(provider: STTProvider, config: dict) -> BaseSTT:
    if provider == STTProvider.WHISPER:
        return WhisperSTT(**config)
    elif provider == STTProvider.MINIMAX:
        return MiniMaxSTT(**config)
    elif provider == STTProvider.SENSEVOICE:
        return SenseVoiceSTT(**config)
    raise ValueError(f"Unknown STT provider: {provider}")
