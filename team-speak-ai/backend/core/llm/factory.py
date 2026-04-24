from enum import Enum
from core.llm.base import BaseLLM
from core.llm.openai_llm import OpenAILLM


class LLMProvider(Enum):
    OPENAI = "openai"


def create_llm(provider: LLMProvider, config: dict) -> BaseLLM:
    if provider == LLMProvider.OPENAI:
        return OpenAILLM(**config)
    raise ValueError(f"Unknown LLM provider: {provider}")
