from typing import AsyncIterator, Optional
from openai import AsyncOpenAI
from core.llm.base import BaseLLM, LLMChunk


class OpenAILLM(BaseLLM):
    """OpenAI 兼容 LLM（支持 MiniMax / OpenAI / DeepSeek 等 OpenAI API 兼容服务）"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.minimaxi.com/v1",
        model: str = "MiniMax-M2.7",
        reasoning_split: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop: Optional[list] = None,
        response_format: Optional[str] = None,
        extra: Optional[dict] = None,
    ):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.reasoning_split = reasoning_split
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.stop = stop or []
        self.response_format = response_format
        self.extra = extra or {}

    def _build_request_kwargs(self, messages: list, stream: bool, **kwargs) -> dict:
        """构建 API 请求参数"""
        req = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        if self.temperature is not None:
            req["temperature"] = self.temperature
        if self.max_tokens is not None:
            req["max_tokens"] = self.max_tokens
        if self.top_p is not None:
            req["top_p"] = self.top_p
        if self.stop:
            req["stop"] = self.stop

        extra_body = {}
        if self.reasoning_split:
            extra_body["reasoning_split"] = True
        extra_body.update(self.extra)

        if extra_body:
            req["extra_body"] = extra_body

        if self.response_format and self.response_format == "json_object":
            req["response_format"] = {"type": "json_object"}

        req.update(kwargs)
        return req

    async def chat(self, messages: list, **kwargs) -> LLMChunk:
        """非流式聊天，返回完整响应"""
        req = self._build_request_kwargs(messages, stream=False, **kwargs)
        response = await self.client.chat.completions.create(**req)

        content = ""
        reasoning = ""
        choice = response.choices[0]

        if choice.message.content:
            content = choice.message.content

        # MiniMax reasoning_details on non-stream
        if hasattr(choice, "reasoning_details") and choice.reasoning_details:
            for detail in choice.reasoning_details:
                if hasattr(detail, "text"):
                    reasoning += detail.text
        # DeepSeek / standard: reasoning_content attr
        if hasattr(choice.message, "reasoning_content") and choice.message.reasoning_content:
            reasoning = choice.message.reasoning_content

        return LLMChunk(content=content, reasoning=reasoning)

    async def chat_stream(self, messages: list, **kwargs) -> AsyncIterator[LLMChunk]:
        """流式聊天，逐块返回"""
        req = self._build_request_kwargs(messages, stream=True, **kwargs)
        stream = await self.client.chat.completions.create(**req)

        reasoning_buffer = ""

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            # MiniMax reasoning_details
            if hasattr(delta, "reasoning_details") and delta.reasoning_details:
                for detail in delta.reasoning_details:
                    text = None
                    if isinstance(detail, dict) and "text" in detail:
                        text = detail["text"]
                    elif hasattr(detail, "text"):
                        text = detail.text
                    if text:
                        reasoning_buffer += text

            # DeepSeek / Anthropic reasoning_content on delta
            if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                reasoning_buffer += delta.reasoning_content

            if delta.content:
                yield LLMChunk(
                    content=delta.content,
                    reasoning=reasoning_buffer,
                )
