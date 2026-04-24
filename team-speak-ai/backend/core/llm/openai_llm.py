from typing import AsyncIterator
from openai import AsyncOpenAI
from core.llm.base import BaseLLM, LLMChunk


class OpenAILLM(BaseLLM):
    """OpenAI 兼容 LLM（支持 MiniMax 等 OpenAI API 兼容服务）"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.minimaxi.com/v1",
        model: str = "MiniMax-M2.7",
        reasoning_split: bool = True,
    ):
        """
        初始化 OpenAI 兼容 LLM

        Args:
            api_key: API 密钥
            base_url: API 基础 URL（MiniMax 兼容端点）
            model: 模型名称
            reasoning_split: 是否分离思考过程（MiniMax 特有）
        """
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.reasoning_split = reasoning_split

    async def chat(self, messages: list, **kwargs) -> LLMChunk:
        """
        同步聊天，返回完整响应

        Args:
            messages: 消息列表
            **kwargs: 其他参数

        Returns:
            LLMChunk: 包含 content 和 reasoning
        """
        extra_body = {}
        if self.reasoning_split:
            extra_body["reasoning_split"] = True

        reasoning_full = ""
        content_full = ""

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            extra_body=extra_body,
            **kwargs
        )

        async for chunk in stream:
            # 处理 reasoning_details（MiniMax 特有）
            if hasattr(chunk.choices[0].delta, "reasoning_details"):
                for detail in chunk.choices[0].delta.reasoning_details or []:
                    if "text" in detail:
                        reasoning_full += detail["text"]

            # 处理 content
            if chunk.choices[0].delta.content:
                content_full += chunk.choices[0].delta.content

        return LLMChunk(content=content_full, reasoning=reasoning_full)

    async def chat_stream(self, messages: list, **kwargs) -> AsyncIterator[LLMChunk]:
        """
        流式聊天，逐块返回

        Args:
            messages: 消息列表
            **kwargs: 其他参数

        Yields:
            LLMChunk: 每个 chunk 包含新增的 content 和累积的 reasoning
        """
        extra_body = {}
        if self.reasoning_split:
            extra_body["reasoning_split"] = True

        reasoning_buffer = ""

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            extra_body=extra_body,
            **kwargs
        )

        async for chunk in stream:
            # 处理 reasoning_details（MiniMax 特有）
            if hasattr(chunk.choices[0].delta, "reasoning_details"):
                for detail in chunk.choices[0].delta.reasoning_details or []:
                    if "text" in detail:
                        reasoning_buffer += detail["text"]

            # 处理 content（只有新增部分）
            if chunk.choices[0].delta.content:
                yield LLMChunk(
                    content=chunk.choices[0].delta.content,
                    reasoning=reasoning_buffer
                )
