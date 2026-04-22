from abc import ABC, abstractmethod


class BaseSTT(ABC):
    @abstractmethod
    async def transcribe(self, audio_data: bytes) -> str:
        """将音频数据转为文本"""

    @abstractmethod
    async def transcribe_stream(self, audio_stream, sample_rate: int):
        """流式转写"""
