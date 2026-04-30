"""
EventEmitter — 向订阅了某个 feature 的 WebSocket 推送实时事件

支持旧格式 ({type, data}) 和新信封格式 ({msg_id, flow_id, type, action, params, ts})。
"""

import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def _now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


class EventEmitter:
    """
    事件发射器
    通过 pipeline engine 的 ws 连接表，向订阅了特定 feature 的客户端推送消息。
    同时兼容旧的 {type, data} 格式和新信封格式。
    """

    def __init__(self, engine, feature_id: str):
        self._engine = engine
        self._feature_id = feature_id

    @property
    def _use_envelope(self) -> bool:
        """从当前执行实例读取信封协议标志"""
        # 尝试从任意实例获取标志（通常只有一个实例在运行）
        for flow_id, instances in self._engine._instances.items():
            if flow_id == self._feature_id or instances.pipeline_def.id == self._feature_id:
                if hasattr(instances, 'use_envelope'):
                    return instances.use_envelope
        return False

    async def _send(self, action: str, params: dict):
        """发送消息到所有订阅该 feature 的 WebSocket 连接"""
        if self._use_envelope:
            message = json.dumps({
                "msg_id": str(uuid.uuid4()),
                "flow_id": self._feature_id,
                "type": "event",
                "action": action,
                "params": params,
                "ts": _now_ts(),
            }, ensure_ascii=False)
        else:
            # 旧格式兼容
            legacy_type_map = {
                "node.status_changed": "node_update",
                "node.completed": "node_complete",
                "node.error": "node_error",
                "pipeline.started": "pipeline_start",
                "pipeline.completed": "pipeline_complete",
                "important_update": "important_update",
                "node.log_entry": "node_log",
            }
            legacy_type = legacy_type_map.get(action, action)
            message = json.dumps({
                "type": legacy_type,
                "data": {
                    "feature_id": self._feature_id,
                    **params,
                },
            }, ensure_ascii=False)

        connections = self._engine.get_ws_connections(self._feature_id)
        for ws in list(connections):
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.warning(f"EventEmitter send error: {e}")
                self._engine.unregister_ws(self._feature_id, ws)

        # 同时广播到 /ws 端点的 flow 订阅者
        await self._engine.broadcast_to_flow(self._feature_id, action, params)

    async def emit_node_status_changed(
        self,
        node_id: str,
        status: str,
        summary: str = "",
        progress: Optional[float] = None,
        data: Optional[dict] = None,
        condition_result: Optional[str] = None,
    ):
        params = {
            "node_id": node_id,
            "status": status,
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
        params = {
            "title": title,
            "content": content,
            "level": event_type,
        }
        if node_id:
            params["node_id"] = node_id
        await self._send("important_update", params)
