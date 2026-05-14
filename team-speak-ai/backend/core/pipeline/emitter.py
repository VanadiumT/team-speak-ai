"""
EventEmitter — 向订阅了某个 feature 的 WebSocket 推送实时事件

通过 engine 的广播回调统一分发，不直接持有 WS 连接。
"""

import logging
from typing import Optional, Union

from core.pipeline.context import NodeState

logger = logging.getLogger(__name__)


class EventEmitter:
    """
    事件发射器
    通过 pipeline engine 的广播回调，向订阅了特定 feature 的客户端推送消息。
    """

    def __init__(self, engine, flow_id: str):
        self._engine = engine
        self._flow_id = flow_id

    async def _send(self, action: str, params: dict):
        """发送消息到所有订阅该 flow 的 WebSocket 连接（通过统一广播回调）"""
        await self._engine.broadcast_to_flow(self._flow_id, action, params)

    async def emit_node_status_changed(
        self,
        node_id: str,
        status: Union[str, NodeState],
        summary: str = "",
        progress: Optional[float] = None,
        data: Optional[dict] = None,
        condition_result: Optional[str] = None,
    ):
        status_str = status.value if isinstance(status, NodeState) else status
        params = {
            "node_id": node_id,
            "status": status_str,
            "summary": summary,
            "progress": progress,
            "data": data or {},
        }
        if condition_result:
            params["condition_result"] = condition_result
        await self._send("node.status_changed", params)

    # 兼容旧 API
    async def emit_node_update(
        self,
        node_id: str,
        status: str,
        summary: str = "",
        progress: Optional[float] = None,
        data: Optional[dict] = None,
    ):
        await self.emit_node_status_changed(
            node_id=node_id, status=status, summary=summary,
            progress=progress, data=data,
        )

    async def emit_node_complete(self, node_id: str, output: dict):
        await self._send("node.completed", {
            "node_id": node_id,
            "output": output,
        })

    async def emit_node_error(self, node_id: str, error: str):
        await self._send("node.error", {
            "node_id": node_id,
            "error": error,
        })

    async def emit_node_log_entry(self, node_id: str, level: str, message: str,
                                  highlight: bool = False):
        """推送节点实时日志"""
        from datetime import datetime as dt
        timestamp = dt.now().strftime("%H:%M:%S")
        await self._send("node.log_entry", {
            "node_id": node_id,
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "highlight": highlight,
        })

    async def emit_pipeline_start(self, execution_id: str):
        await self._send("pipeline.started", {
            "execution_id": execution_id,
        })

    async def emit_pipeline_complete(self, execution_id: str):
        await self._send("pipeline.completed", {
            "execution_id": execution_id,
        })

    async def emit_important_update(self, title: str, content: str,
                                    event_type: str = "info", node_id: str = None):
        from core.app_context import get_app_context
        nm = get_app_context().notification_manager
        saved = nm.save(self._flow_id, title, content, event_type, node_id)

        params = {
            "notification_id": saved["id"],
            "title": title,
            "content": content,
            "level": event_type,
            "timestamp": saved["timestamp"],
        }
        if node_id:
            params["node_id"] = node_id
        await self._send("important_update", params)
