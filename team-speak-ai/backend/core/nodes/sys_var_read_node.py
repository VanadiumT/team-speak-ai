"""
SysVarRead 节点 — 读取系统变量

从 SysVarManager 读取全局持久化变量。
"""

import logging

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry

logger = logging.getLogger(__name__)


@NodeRegistry.register("sys_var_read")
class SysVarReadNode(BaseNode):
    """读取系统变量节点"""

    node_type = "sys_var_read"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        self.node_id = context.node_id
        from core.app_context import get_app_context

        cfg = context.node_config or self.config
        key = cfg.get("key", "")
        default = cfg.get("default_value", "")

        if not key:
            self._log_warning("未配置变量 key")
            await emit.emit_node_log_entry(context.node_id, "warn", "未配置变量 key")
            return NodeOutput(data={"value": default, "key": ""}, trigger_next=True)

        svm = get_app_context().sys_var_manager
        value = svm.get(key, default)

        self._log_info(f"读取系统变量 {key} = {value}")
        await emit.emit_node_log_entry(context.node_id, "info", f"读取系统变量 {key} = {value}")
        await emit.emit_node_status_changed(
            context.node_id, "completed",
            summary=f"{key} = {value}",
            data={"key": key, "value": value},
        )

        return NodeOutput(data={"value": value, "key": key}, trigger_next=True)
