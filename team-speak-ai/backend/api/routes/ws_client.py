import logging
from typing import Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.event_bus import event_bus
from api.routes.ws_teamspeak import ts_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws/client", tags=["client"])


class ClientSession:
    """客户端会话"""

    def __init__(self, client_id: str, websocket: WebSocket):
        self.client_id = client_id
        self.websocket = websocket
        self.subscribed_events: set = set()
        self.metadata: Dict = {}

    async def send(self, event_type: str, data: dict):
        """发送消息到客户端"""
        try:
            await self.websocket.send_json({
                "type": event_type,
                "data": data,
                "timestamp": self._get_timestamp()
            })
        except Exception as e:
            logger.error(f"Failed to send message to {self.client_id}: {e}")

    @staticmethod
    def _get_timestamp():
        from datetime import datetime
        return int(datetime.now().timestamp() * 1000)


# 客户端会话管理
client_sessions: Dict[str, ClientSession] = {}


@router.websocket("")
async def client_websocket(websocket: WebSocket):
    """前端 WebSocket 端点"""
    await websocket.accept()
    client_id = str(id(websocket))
    session = ClientSession(client_id, websocket)
    client_sessions[client_id] = session

    await event_bus.register_websocket(client_id, websocket)
    logger.info(f"Client connected: {client_id}")

    await session.send("teamspeak_connected", {"connected": ts_client.connected})

    try:
        while True:
            data = await websocket.receive_json()
            await handle_client_message(client_id, session, data)
    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"Client error {client_id}: {e}")
    finally:
        if client_id in client_sessions:
            del client_sessions[client_id]
        await event_bus.unregister_websocket(client_id)


async def handle_client_message(client_id: str, session: ClientSession, data: dict):
    """处理客户端消息"""
    msg_type = data.get("type", "")
    msg_data = data.get("data", {})

    logger.debug(f"Received from {client_id}: {msg_type}")

    if msg_type == "ping":
        await session.send("pong", {"server_time": session._get_timestamp()})

    elif msg_type == "subscribe":
        # 订阅事件
        events = msg_data.get("events", []) if isinstance(msg_data, dict) else [msg_data]
        for event in events:
            session.subscribed_events.add(event)
            event_bus.subscribe(event, client_id)
        await session.send("subscribed", {"events": list(session.subscribed_events)})

    elif msg_type == "unsubscribe":
        # 取消订阅
        events = msg_data.get("events", []) if isinstance(msg_data, dict) else [msg_data]
        for event in events:
            session.subscribed_events.discard(event)
            event_bus.unsubscribe(event, client_id)
        await session.send("unsubscribed", {"events": list(session.subscribed_events)})

    elif msg_type == "teamspeak_connect":
        # 请求连接到 TeamSpeak
        from api.routes.ws_teamspeak import ts_client
        url = msg_data.get("url") if isinstance(msg_data, dict) else None
        success = await ts_client.connect(url)
        if success:
            await session.send("teamspeak_status", {
                "status": "connected",
                "url": str(ts_client.ws.remote_address) if ts_client.ws else None
            })
        else:
            await session.send("teamspeak_status", {
                "status": "error",
                "message": "Failed to connect to TeamSpeak"
            })

    elif msg_type == "teamspeak_disconnect":
        # 请求断开 TeamSpeak 连接
        from api.routes.ws_teamspeak import ts_client
        await ts_client.disconnect()
        await session.send("teamspeak_status", {"status": "disconnected"})

    elif msg_type == "get_status":
        # 获取状态
        from api.routes.ws_teamspeak import ts_client
        await session.send("status", {
            "teamspeak_connected": ts_client.connected,
            "client_id": client_id,
            "subscribed_events": list(session.subscribed_events)
        })

    elif msg_type == "teamspeak_control":
        # 发送 TeamSpeak 控制命令
        from api.routes.ws_teamspeak import ts_client
        action = msg_data.get("action", "") if isinstance(msg_data, dict) else ""
        params = msg_data.get("params", {}) if isinstance(msg_data, dict) else {}
        await ts_client.send_control(action, **params)
        await session.send("control_sent", {"action": action})

    else:
        # 未知消息类型，广播到所有订阅者
        await event_bus.broadcast_to_subscribers(msg_type, msg_data, exclude_client=client_id)


@router.get("/sessions")
async def list_sessions():
    """获取当前连接的所有客户端会话"""
    return {
        "count": len(client_sessions),
        "sessions": [
            {
                "client_id": sid,
                "subscribed_events": list(s.subscribed_events),
                "metadata": s.metadata
            }
            for sid, s in client_sessions.items()
        ]
    }


@router.get("/sessions/{client_id}")
async def get_session(client_id: str):
    """获取指定客户端会话详情"""
    if client_id in client_sessions:
        session = client_sessions[client_id]
        return {
            "client_id": client_id,
            "subscribed_events": list(session.subscribed_events),
            "metadata": session.metadata
        }
    return {"error": "Session not found"}


async def broadcast_teamspeak_event(event_type: str, data: dict):
    """广播 TeamSpeak 事件到订阅者"""
    message = {
        "type": event_type,
        "data": data
    }
    await event_bus.broadcast_to_subscribers(event_type, data)


async def broadcast_status_update(status: str, details: dict = None):
    """广播状态更新"""
    await broadcast_teamspeak_event("status_update", {
        "status": status,
        "details": details or {}
    })
