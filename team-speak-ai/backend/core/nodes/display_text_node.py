"""
DisplayText 节点 — 文本显示/输入

支持静态文本和透传两种模式，用于在流程中显示和传递文本。
"""

import logging
import re

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry

logger = logging.getLogger(__name__)

_VAR_PATTERN = re.compile(r'\$(param|sys)\.(\w+)')


def _resolve_vars(text: str, context: NodeContext) -> str:
    """Replace $param.key and $sys.key with actual values."""
    from core.variables.manager import get_sys_var_manager

    def replacer(match):
        var_type = match.group(1)
        key = match.group(2)
        if var_type == "param":
            return str(context.accumulated_context.get(key, match.group(0)))
        else:
            svm = get_sys_var_manager()
            return str(svm.get(key, match.group(0)))

    return _VAR_PATTERN.sub(replacer, text)


@NodeRegistry.register("display_text")
class DisplayTextNode(BaseNode):
    """文本显示节点"""

    node_type = "display_text"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        mode = self.config.get("mode", "passthrough")
        static_text = self.config.get("text", "")

        upstream_text = context.inputs.get("text")
        if mode == "passthrough" and upstream_text is not None:
            text = str(upstream_text)
        else:
            text = _resolve_vars(static_text, context)

        await emit.emit_node_status_changed(context.node_id, "processing")

        await emit.emit_node_log_entry(
            context.node_id, "info",
            f"文本输出: {text[:60]}{'...' if len(text) > 60 else ''}",
        )

        await emit.emit_node_status_changed(
            context.node_id, "completed",
            summary=text[:40] + ("..." if len(text) > 40 else ""),
            data={"text": text},
        )

        return NodeOutput(data={"text": text}, trigger_next=True)
