"""
InputImage 节点 — 接收用户上传的图片

用户在前端通过文件选择器上传图片后，
前端发送 node_action(upload, image_data) 触发此节点。
"""

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry
import logging

logger = logging.getLogger(__name__)


@NodeRegistry.register("input_image")
class InputImageNode(BaseNode):
    """图片输入节点"""

    node_type = "input_image"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        file_input = context.inputs.get("file", {})
        notify_on_reach = self.config.get("notify_on_reach", True)

        # file_input can be a string (base64 data), a dict with metadata, or empty
        if isinstance(file_input, str):
            filename = context.inputs.get("filename", "uploaded.png")
            mime_type = context.inputs.get("mime_type", "image/png")
            file_data = file_input
        elif isinstance(file_input, dict):
            file_data = file_input.get("data", "")
            filename = file_input.get("filename", "uploaded.png")
            mime_type = file_input.get("mime_type", "image/png")
        else:
            file_data = ""
            filename = "unknown"
            mime_type = ""

        # No file uploaded yet — pause and notify user
        if not file_data:
            if notify_on_reach:
                await emit.emit_important_update(
                    "请上传图片",
                    "流程已到达上传图片节点，请上传图片后继续。",
                    event_type="info",
                    node_id=context.node_id,
                )

            await emit.emit_node_log_entry(
                context.node_id, "info",
                "等待用户上传图片...",
            )

            await emit.emit_node_status_changed(
                context.node_id, "processing",
                summary="等待上传...",
            )

            return NodeOutput(data={"status": "waiting"}, trigger_next=False)

        # Ensure data is string, not bytes
        if isinstance(file_data, bytes):
            import base64
            file_data = base64.b64encode(file_data).decode("ascii")

        result = {
            "file": file_data,
            "filename": filename,
            "mime_type": mime_type,
        }

        await emit.emit_node_status_changed(context.node_id, "processing")

        await emit.emit_node_log_entry(
            context.node_id, "info",
            f"已接收图片: {filename}",
        )

        await emit.emit_node_status_changed(
            context.node_id, "completed",
            summary=f"已接收: {filename}",
            data=result,
        )

        return NodeOutput(data=result, trigger_next=True)
