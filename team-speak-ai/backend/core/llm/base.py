from abc import ABC, abstractmethod
from typing import AsyncIterator
from dataclasses import dataclass


@dataclass
class LLMChunk:
    """LLM 流式输出块"""
    content: str = ""      # 实际回复文本
    reasoning: str = ""    # 思考过程（前端显示用）


class BaseLLM(ABC):
    @abstractmethod
    async def chat(self, messages: list, **kwargs) -> LLMChunk:
        """同步聊天，返回完整响应（含 reasoning）"""

    @abstractmethod
    async def chat_stream(self, messages: list, **kwargs) -> AsyncIterator[LLMChunk]:
        """流式聊天，逐块返回（同时含 content 和 reasoning）"""
