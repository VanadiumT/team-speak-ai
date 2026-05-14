"""WebSocket 通信相关异常"""
from __future__ import annotations

from core.exceptions.base import AppBaseException


class WSProtocolError(AppBaseException):
    """WebSocket 协议错误（消息格式错误、未知 action 等）"""

    error_code = "WS_PROTOCOL"

    def __init__(self, detail: str):
        super().__init__(message=f"WebSocket protocol error: {detail}")


class WSClientDisconnected(AppBaseException):
    """WebSocket 客户端断开连接"""

    error_code = "WS_CLIENT_DISCONNECTED"

    def __init__(self, client_id: str = ""):
        super().__init__(
            message=f"WebSocket client disconnected: {client_id}",
            context={"client_id": client_id},
        )
