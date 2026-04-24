"""
EventEmitter — 向订阅了某个 feature 的 WebSocket 推送实时事件
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EventEmitter:
    """
    事件发射器
    通过 pipeline engine 的 ws 连接表，向订阅了特定 feature 的客户端推送消息
    """

    def __init__(self, engine, feature_id: str):
        self._engine = engine
        self._feature_id = feature_id

    async def _send(self, event_type: str, data: dict):
        """发送消息到所有订阅该 feature 的 WebSocket 连接"""
        message = json.dumps({
            "type": event_type,
            "data": {
                "feature_id": self._feature_id,
                **data
            }
        })
        connections = self._engine.get_ws_connections(self._feature_id)
        for ws in list(connections):
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.warning(f"EventEmitter send error: {e}")
                self._engine.unregister_ws(self._feature_id, ws)

    async def emit_node_update(
        self,
        node_id: str,
        status: str,
        summary: str = "",
        progress: Optional[float] = None,
        data: Optional[dict] = None,
    ):
        await self._send("node_update", {
            "node_id": node_id,
            "status": status,
            "summary": summary,
            "progress": progress,
            "data": data or {},
        })

    async def emit_node_complete(self, node_id: str, output: dict):
        await self._send("node_complete", {
            "node_id": node_id,
            "output": output,
        })

    async def emit_node_error(self, node_id: str, error: str):
        await self._send("node_error", {
            "node_id": node_id,
            "error": error,
        })

    async def emit_pipeline_start(self, execution_id: str):
        await self._send("pipeline_start", {
            "execution_id": execution_id,
        })

    async def emit_pipeline_complete(self, execution_id: str):
        await self._send("pipeline_complete", {
            "execution_id": execution_id,
        })

    async def emit_important_update(self, title: str, content: str, event_type: str = "info"):
        await self._send("important_update", {
            "type": event_type,
            "title": title,
            "content": content,
        })
