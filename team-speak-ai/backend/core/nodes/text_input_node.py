"""
TextInput 节点 — 文本输入

支持两种模式：
- static: 流程运行前配置固定文本，支持 $param.key / $sys.key 变量解析
- interactive: 流程到达时暂停，通知用户输入文本，确认后继续
"""

import logging

from core.nodes.base import BaseNode
from core.nodes.display_text_node import _resolve_vars
from core.pipeline.context import NodeContext, NodeOutput, NodeState
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry

logger = logging.getLogger(__name__)


@NodeRegistry.register("text_input")
class TextInputNode(BaseNode):
    """文本输入节点"""

    node_type = "text_input"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        cfg = context.node_config or self.config
        mode = cfg.get("mode", "static")
        static_text = cfg.get("text", "")
        notify_on_reach = cfg.get("notify_on_reach", True)

        # User-provided text takes priority (from interactive input or upstream)
        user_text = context.inputs.get("text")

        if mode == "interactive":
            if user_text:
                # User has submitted text — process and continue
                text = str(user_text)

                await emit.emit_node_status_changed(context.node_id, NodeState.PROCESSING)

                await emit.emit_node_log_entry(
                    context.node_id, "info",
                    f"已接收文本: {text[:60]}{'...' if len(text) > 60 else ''}",
                )

                await emit.emit_node_status_changed(
                    context.node_id, "completed",
                    summary=text[:40] + ("..." if len(text) > 40 else ""),
                    data={"text": text},
                )

                return NodeOutput(data={"text": text}, trigger_next=True)
            else:
                # No text yet — pause and notify user
                if notify_on_reach:
                    await emit.emit_important_update(
                        "请输入文本",
                        "流程已到达文本输入节点，请输入文本后继续。",
                        event_type="info",
                        node_id=context.node_id,
                    )

                await emit.emit_node_log_entry(
                    context.node_id, "info",
                    "等待用户输入文本...",
                )

                await emit.emit_node_status_changed(
                    context.node_id, "processing",
                    summary="等待输入...",
                )

                return NodeOutput(data={"status": "waiting"}, trigger_next=False)
        else:
            # Static mode — resolve and output immediately
            text = _resolve_vars(static_text, context)

            await emit.emit_node_status_changed(context.node_id, NodeState.PROCESSING)

            await emit.emit_node_log_entry(
                context.node_id, "info",
                f"文本输入: {text[:60]}{'...' if len(text) > 60 else ''}",
            )

            await emit.emit_node_status_changed(
                context.node_id, "completed",
                summary=text[:40] + ("..." if len(text) > 40 else ""),
                data={"text": text},
            )

            return NodeOutput(data={"text": text}, trigger_next=True)
