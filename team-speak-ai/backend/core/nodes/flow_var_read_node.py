"""
FlowVarRead 节点 — 读取流程参数

从 accumulated_context 中读取流程参数（由 start 节点或 flow_var_write 节点写入）。
"""

import logging

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry

logger = logging.getLogger(__name__)


@NodeRegistry.register("flow_var_read")
class FlowVarReadNode(BaseNode):
    """读取流程参数节点"""

    node_type = "flow_var_read"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        cfg = context.node_config or self.config
        key = cfg.get("key", "")
        default = cfg.get("default_value", "")

        if not key:
            await emit.emit_node_log_entry(context.node_id, "warn", "未配置参数 key")
            return NodeOutput(data={"value": default, "key": ""}, trigger_next=True)

        value = context.accumulated_context.get(key, default)

        await emit.emit_node_log_entry(context.node_id, "info", f"读取流程参数 {key} = {value}")
        await emit.emit_node_status_changed(
            context.node_id, "completed",
            summary=f"{key} = {value}",
            data={"key": key, "value": value},
        )

        return NodeOutput(data={"value": value, "key": key}, trigger_next=True)
