"""
SysVarWrite 节点 — 写入系统变量

将上游节点的输出写入 SysVarManager（持久化到磁盘）。
"""

import logging

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry

logger = logging.getLogger(__name__)


@NodeRegistry.register("sys_var_write")
class SysVarWriteNode(BaseNode):
    """写入系统变量节点"""

    node_type = "sys_var_write"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        from core.app_context import get_app_context

        cfg = context.node_config or self.config
        key = cfg.get("key", "")
        merge_mode = cfg.get("merge_mode", "overwrite")

        if not key:
            await emit.emit_node_log_entry(context.node_id, "warn", "未配置变量 key")
            return NodeOutput(data={"value": None, "key": ""}, trigger_next=True)

        value = context.inputs.get("data")
        if value is None:
            await emit.emit_node_log_entry(context.node_id, "warn", f"未收到数据，跳过写入变量 {key}")
            return NodeOutput(data={"value": None, "key": key}, trigger_next=True)
        svm = get_app_context().sys_var_manager
        svm.set(key, value, merge_mode)

        await emit.emit_node_log_entry(context.node_id, "info", f"写入系统变量 {key} = {value}")
        await emit.emit_node_status_changed(
            context.node_id, "completed",
            summary=f"{key} = {value}",
            data={"key": key, "value": value},
        )

        return NodeOutput(data={"value": value, "key": key}, trigger_next=True)
