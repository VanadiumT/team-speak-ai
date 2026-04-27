"""
Context Build 节点 — 构建 LLM 上下文

将上游节点数据（OCR 文本 + STT 监听文本 + Skill 提示词）
合并为一个完整的 LLM messages 数组，传递给 LLM 节点。
"""

import logging
from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry
from config import settings

logger = logging.getLogger(__name__)


@NodeRegistry.register("context_build")
class ContextBuildNode(BaseNode):
    """上下文构建节点"""

    node_type = "context_build"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        # 从输入获取
        ocr_text = context.inputs.get("ocr_text", "")
        stt_text = context.inputs.get("stt_text", "")

        # 从 accumulated_context 获取（由 stt_listen 累积）
        if not stt_text and context.accumulated_context.get("stt_history"):
            stt_text = "\n".join(context.accumulated_context["stt_history"][-20:])

        # 从 accumulated_context 读取 skill_prompt（由 engine.start_pipeline 存入）
        skill_prompt = context.accumulated_context.get("skill_prompt", "")

        # 构建 system prompt
        system_parts = ["你是一个 TeamSpeak 语音助手，请用中文简洁回复。"]
        if skill_prompt:
            system_parts.append(f"\n## 技能规则\n{skill_prompt}")

        # 构建上下文
        context_parts = []
        if ocr_text:
            context_parts.append(f"## OCR 识别结果\n{ocr_text}")
        if stt_text:
            context_parts.append(f"## 当前语音对话\n{stt_text}")

        user_message = ""
        if context_parts:
            user_message = "以下为当前上下文信息：\n\n" + "\n\n".join(context_parts)
        else:
            user_message = "你好"

        messages = [
            {"role": "system", "content": "\n".join(system_parts)},
            {"role": "user", "content": user_message},
        ]

        # 插入历史对话（结构化消息）
        llm_messages = context.accumulated_context.get("llm_messages", [])
        for msg in llm_messages[-6:]:  # 最近 3 轮
            if isinstance(msg, dict) and "role" in msg:
                messages.append(msg)

        await emit.emit_node_update(
            context.node_id,
            "completed",
            f"上下文已构建: OCR={len(ocr_text)}字符, STT={len(stt_text)}字符",
            data={"ocr_text": ocr_text, "stt_text": stt_text, "message_count": len(messages)},
        )

        return NodeOutput({
            "messages": messages,
            "ocr_text": ocr_text,
            "stt_text": stt_text,
        })
