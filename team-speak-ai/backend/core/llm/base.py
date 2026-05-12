from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional
from dataclasses import dataclass, field


@dataclass
class LLMChunk:
    """LLM 流式输出块"""
    content: str = ""      # 实际回复文本
    reasoning: str = ""    # 思考过程（前端显示用）
    images: list = field(default_factory=list)  # 图片输出（多模态回复）


class BaseLLM(ABC):
    @abstractmethod
    async def chat(self, messages: list, **kwargs) -> LLMChunk:
        """非流式聊天，返回完整响应（含 reasoning）"""

    @abstractmethod
    async def chat_stream(self, messages: list, **kwargs) -> AsyncIterator[LLMChunk]:
        """流式聊天，逐块返回（同时含 content 和 reasoning）"""
