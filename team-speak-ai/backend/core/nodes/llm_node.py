"""
LLM 节点 — 调用大模型生成文本

支持流式输出，实时推送内容片段和思考过程到前端。
"""

import logging
from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry
from core.llm.factory import LLMProvider, create_llm
from config import settings

logger = logging.getLogger(__name__)


@NodeRegistry.register("llm")
class LLMNode(BaseNode):
    """大模型文本生成节点"""

    node_type = "llm"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        messages = context.inputs.get("messages", [])
        if not messages:
            messages = [{"role": "user", "content": "你好"}]

        model_cfg = context.node_config.get("model", settings.openai_model)
        reasoning_split = context.node_config.get(
            "reasoning_split", settings.openai_reasoning_split
        )

        llm = self._get_llm(model_cfg, reasoning_split)

        await emit.emit_node_update(
            context.node_id,
            "processing",
            "AI 思考中...",
            data={"mode": "thinking"},
        )

        full_content = ""
        full_reasoning = ""

        try:
            async for chunk in llm.chat_stream(messages):
                if chunk.content:
                    full_content += chunk.content
                if chunk.reasoning:
                    full_reasoning = chunk.reasoning

                # 每收到一个 chunk 就推送到前端
                await emit.emit_node_update(
                    context.node_id,
                    "processing",
                    f"生成中 ({len(full_content)} 字)...",
                    progress=min(len(full_content) / 500, 0.95),
                    data={
                        "mode": "generating",
                        "content_chunk": chunk.content,
                        "content_full": full_content,
                        "reasoning": full_reasoning,
                    },
                )

            # 完成
            await emit.emit_node_update(
                context.node_id,
                "completed",
                f"生成完成 ({len(full_content)} 字)",
                data={
                    "content": full_content,
                    "reasoning": full_reasoning,
                },
            )

            return NodeOutput({
                "response": full_content,
                "reasoning": full_reasoning,
            })

        except Exception as e:
            logger.exception(f"LLM error")
            await emit.emit_node_error(context.node_id, str(e))
            return NodeOutput({"response": f"错误: {str(e)}", "reasoning": ""}, trigger_next=False)

    @staticmethod
    def _get_llm(model: str, reasoning_split: bool):
        provider = LLMProvider(settings.llm_provider)
        config = {
            "api_key": settings.openai_api_key,
            "base_url": settings.openai_base_url,
            "model": model,
            "reasoning_split": reasoning_split,
        }
        return create_llm(provider, config)
