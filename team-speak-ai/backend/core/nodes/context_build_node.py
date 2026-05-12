"""
上下文构建器 — 将多个上游节点数据合并为 LLM messages 数组

消息顺序: system → 历史对话(chat-in) → 当前信息(ctx-in*)
"""

import logging
from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry

logger = logging.getLogger(__name__)


@NodeRegistry.register("context_build")
class ContextBuildNode(BaseNode):
    """上下文构建节点"""

    node_type = "context_build"

    @staticmethod
    def _input_key(port_id: str) -> str:
        # 复用 _port_input_key 的对应逻辑：剥离 -in 后缀
        # 但引擎的 input_mapping.as_field 存的是完整 port_id，不带 -in 后缀
        # 所以直接返回 port_id 本身，避免双重剥离
        # ctx-in1 → 存为 "ctx-in1"，读为 "ctx-in1"
        return port_id

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        # 1. System prompt: 仅当 system-in 有输入时才添加
        messages = []
        system_text = context.inputs.get("system", "")
        if system_text:
            messages.append({"role": "system", "content": system_text})

        # 2. 历史对话 (chat-in 端口)
        chat_messages = context.inputs.get("chat", [])
        if isinstance(chat_messages, list):
            for msg in chat_messages:
                if isinstance(msg, dict) and "role" in msg:
                    messages.append(msg)
        else:
            # fallback: accumulated_context
            llm_messages = context.accumulated_context.get("llm_messages", [])
            for msg in llm_messages[-6:]:
                if isinstance(msg, dict) and "role" in msg:
                    messages.append(msg)

        # 3. 当前信息片段: req-in (用户提示词) + ctx-in* (可重复端口)
        req_text = context.inputs.get("req", "")
        port_labels = context.node_config.get("_port_labels", {})
        repeatable_ports = context.node_config.get("_repeatable_ports", {}).get("ctx", [])

        user_parts = []
        total_chars = 0
        # 用户提示词在最前
        if req_text:
            user_parts.append(f"【要求】\n{req_text}")
            total_chars += len(str(req_text))
        # 上下文信息片段
        for i, port_id in enumerate(repeatable_ports, 1):
            key = self._input_key(port_id)
            value = context.inputs.get(key, "")
            if value:
                label = port_labels.get(port_id, f"信息{i}")
                user_parts.append(f"【{label}】\n{value}")
                total_chars += len(str(value))

        user_message = "\n\n".join(user_parts) if user_parts else "你好"
        messages.append({"role": "user", "content": user_message})

        await emit.emit_node_update(
            context.node_id,
            "completed",
            f"上下文已构建: {len(user_parts)}个片段, {total_chars}字符, {len(messages)}条消息",
            data={
                "fragment_count": len(user_parts),
                "total_chars": total_chars,
                "message_count": len(messages),
                "user_message": user_message,
                "messages": messages,
            },
        )

        return NodeOutput({"messages": messages})
