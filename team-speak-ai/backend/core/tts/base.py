from abc import ABC, abstractmethod


class BaseTTS(ABC):
    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """将文本转为语音"""

    @abstractmethod
    async def synthesize_stream(self, text: str):
        """流式合成"""
