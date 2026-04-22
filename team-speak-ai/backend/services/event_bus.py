from typing import Dict, Set, Optional
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)


class EventBus:
    """事件总线 - 管理 WebSocket 客户端和事件订阅"""

    def __init__(self):
        self._websockets: Dict[str, WebSocket] = {}
        self._subscribers: Dict[str, Set[str]] = {}

    async def register_websocket(self, client_id: str, websocket: WebSocket):
        """注册 WebSocket 客户端"""
        self._websockets[client_id] = websocket
        logger.debug(f"WebSocket registered: {client_id}")

    async def unregister_websocket(self, client_id: str):
        """注销 WebSocket 客户端"""
        if client_id in self._websockets:
            del self._websockets[client_id]

        # 同时取消该客户端的所有订阅
        for event_type in list(self._subscribers.keys()):
            self._subscribers[event_type].discard(client_id)
            if not self._subscribers[event_type]:
                del self._subscribers[event_type]

        logger.debug(f"WebSocket unregistered: {client_id}")

    async def broadcast(self, event_type: str, data: dict):
        """广播事件到所有已连接客户端"""
        message = json.dumps({
            "type": event_type,
            "data": data
        })
        for client_id, websocket in list(self._websockets.items()):
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to {client_id}: {e}")

    async def broadcast_to_client(self, client_id: str, event_type: str, data: dict):
        """发送事件到指定客户端"""
        if client_id in self._websockets:
            message = json.dumps({
                "type": event_type,
                "data": data
            })
            try:
                await self._websockets[client_id].send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to {client_id}: {e}")

    async def broadcast_to_subscribers(
        self,
        event_type: str,
        data: dict,
        exclude_client: Optional[str] = None
    ):
        """广播事件到订阅了该事件的客户端"""
        message = json.dumps({
            "type": event_type,
            "data": data
        })

        subscribers = self._subscribers.get(event_type, set())
        for client_id in list(subscribers):
            if client_id == exclude_client:
                continue
            if client_id in self._websockets:
                try:
                    await self._websockets[client_id].send_text(message)
                except Exception as e:
                    logger.warning(f"Failed to send to subscriber {client_id}: {e}")

    def subscribe(self, event_type: str, client_id: str):
        """订阅事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = set()
        self._subscribers[event_type].add(client_id)
        logger.debug(f"Client {client_id} subscribed to {event_type}")

    def unsubscribe(self, event_type: str, client_id: str):
        """取消订阅"""
        if event_type in self._subscribers:
            self._subscribers[event_type].discard(client_id)
            if not self._subscribers[event_type]:
                del self._subscribers[event_type]
        logger.debug(f"Client {client_id} unsubscribed from {event_type}")

    def get_subscribers(self, event_type: str) -> Set[str]:
        """获取某事件的订阅者"""
        return self._subscribers.get(event_type, set()).copy()

    def get_all_subscriptions(self) -> Dict[str, Set[str]]:
        """获取所有订阅关系"""
        return {k: v.copy() for k, v in self._subscribers.items()}


event_bus = EventBus()
