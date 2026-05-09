"""
FlowVarWrite 节点 — 写入流程参数

将上游节点的输出写入 accumulated_context 中的流程参数。
"""

import logging

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry

logger = logging.getLogger(__name__)


@NodeRegistry.register("flow_var_write")
class FlowVarWriteNode(BaseNode):
    """写入流程参数节点"""

    node_type = "flow_var_write"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        key = self.config.get("key", "")
        merge_mode = self.config.get("merge_mode", "overwrite")

        if not key:
            await emit.emit_node_log_entry(context.node_id, "warn", "未配置参数 key")
            return NodeOutput(data={"value": None, "key": ""}, trigger_next=True)

        value = context.inputs.get("data")

        if merge_mode == "append":
            existing = context.accumulated_context.get(key, [])
            if not isinstance(existing, list):
                existing = [existing]
            existing.append(value)
            context.accumulated_context[key] = existing
        else:
            context.accumulated_context[key] = value

        await emit.emit_node_log_entry(context.node_id, "info", f"写入流程参数 {key} = {value}")
        await emit.emit_node_status_changed(
            context.node_id, "completed",
            summary=f"{key} = {value}",
            data={"key": key, "value": value},
        )

        return NodeOutput(data={"value": value, "key": key}, trigger_next=True)
