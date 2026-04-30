"""
STT History 节点 — 历史语音记录关键词判断

接收上游 STT 识别文本，维护历史窗口，
检测关键词后触发下游（ContextBuild → LLM → TTS → Output）。
"""

import logging

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry

logger = logging.getLogger(__name__)


@NodeRegistry.register("stt_history")
class STTHistoryNode(BaseNode):
    """STT 历史记录 + 关键词判断节点"""

    node_type = "stt_history"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        max_entries = context.node_config.get("max_entries", 20)
        keywords = context.node_config.get("keywords", [])

        # 从上游获取文本
        input_text = context.inputs.get("text", "")
        if not input_text:
            input_text = context.inputs.get("stt_text", "")

        # 获取历史窗口
        history = context.accumulated_context.get("stt_history", [])
        if isinstance(history, list):
            history = list(history)
        else:
            history = []

        if input_text.strip():
            history.append(input_text.strip())

        # 限制历史窗口大小
        if len(history) > max_entries:
            history = history[-max_entries:]

        # 更新累积上下文
        context.accumulated_context["stt_history"] = history

        combined = "\n".join(history)

        await emit.emit_node_log_entry(
            context.node_id, "info",
            f"历史记录: {len(history)} 条，共 {len(combined)} 字符",
        )

        # 关键词检测
        if keywords:
            for kw in keywords:
                if kw in combined:
                    logger.info(f"STT History [{context.node_id}]: keyword '{kw}' detected")
                    await emit.emit_node_update(
                        context.node_id,
                        "completed",
                        f"关键词 '{kw}' 触发!",
                        data={"trigger_keyword": kw, "history": history},
                        condition_result="matched",
                    )
                    await emit.emit_important_update(
                        "关键词触发",
                        f"STT History 检测到关键词 '{kw}'，已触发 AI 流程",
                        "warning",
                        context.node_id,
                    )
                    return NodeOutput({
                        "history": history,
                        "trigger_keyword": kw,
                        "condition_result": "matched",
                    })

            # 未匹配关键词
            await emit.emit_node_update(
                context.node_id,
                "completed",
                "无关键词匹配",
                data={"history": history},
                condition_result="skipped",
            )
            return NodeOutput({
                "history": history,
                "condition_result": "skipped",
            })

        # 无关键词配置，默认触发
        await emit.emit_node_update(
            context.node_id,
            "completed",
            f"已收集 {len(history)} 条历史记录",
            data={"history": history},
        )
        return NodeOutput({"history": history})
