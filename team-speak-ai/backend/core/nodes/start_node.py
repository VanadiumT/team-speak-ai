"""
Start 节点 — 流程起点

流程启动时自动执行，将 init_params 写入 accumulated_context。
"""

import logging

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput, NodeState
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry

logger = logging.getLogger(__name__)


@NodeRegistry.register("start")
class StartNode(BaseNode):
    """流程开始节点 — 流程启动时自动执行"""

    node_type = "start"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        await emit.emit_node_status_changed(context.node_id, NodeState.PROCESSING)

        cfg = context.node_config or self.config
        init_params = cfg.get("init_params", {})

        if init_params:
            from core.app_context import get_app_context
            fm = get_app_context().flow_manager
            await fm.update_flow_params(context.flow_id, init_params)

            for key, value in init_params.items():
                context.accumulated_context[key] = value

        param_count = len(init_params)
        await emit.emit_node_log_entry(
            context.node_id, "info",
            f"流程启动，写入 {param_count} 个参数" + (f": {list(init_params.keys())}" if init_params else ""),
        )

        await emit.emit_node_status_changed(
            context.node_id, "completed",
            summary=f"已触发" + (f"，写入 {param_count} 个参数" if param_count else ""),
            data={"params": init_params},
        )

        return NodeOutput(data={"params": init_params}, trigger_next=True)
