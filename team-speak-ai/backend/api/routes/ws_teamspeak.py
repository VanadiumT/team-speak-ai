"""
TeamSpeak WebSocket 中继

职责（精简后）：
1. 连接 TeamSpeak Voice Bridge (Java, port 8080)
2. 接收 TS 音频 → 中继到前端 + 发布到 AudioBus
3. 接收前端/引擎的 SEND_VOICE → 发送到 TS 播放
4. 心跳保活 + 重连

不再包含 STT 逻辑（已移至 pipeline stt_listen 节点）
"""

import json
import asyncio
import logging
from typing import Optional, AsyncIterator
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import settings
from core.audio.audio_bus import audio_bus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["teamspeak"])


class TeamSpeakWebSocket:
    """TeamSpeak WebSocket 客户端"""

    def __init__(self):
        self.ws: Optional[WebSocket] = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self._should_reconnect = True

    async def connect(self, url: str = None) -> bool:
        url = url or settings.ts_ws_url
        try:
            import websockets
            self.ws = await websockets.connect(url)
            self.connected = True
            self.reconnect_attempts = 0
            logger.info(f"Connected to TeamSpeak WebSocket: {url}")
            return True
        except Exception as e:
            self.connected = False
            logger.error(f"Failed to connect to TeamSpeak WebSocket: {e}")
            return False

    async def disconnect(self) -> None:
        self._should_reconnect = False
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.connected = False
            logger.info("Disconnected from TeamSpeak WebSocket")

    async def reconnect(self, url: str = None) -> bool:
        while self._should_reconnect and self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            wait_time = min(30, settings.ts_reconnect_interval * self.reconnect_attempts)
            logger.info(f"Reconnecting in {wait_time}s (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
            await asyncio.sleep(wait_time)
            if await self.connect(url):
                return True
        logger.error("Max reconnection attempts reached")
        return False

    async def receive_message(self) -> AsyncIterator[dict]:
        if not self.ws:
            return
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    yield data
                except json.JSONDecodeError:
                    yield {"type": "BINARY", "data": message}
        except Exception as e:
            logger.error(f"Receive error: {e}")

    async def send_voice(self, data: bytes) -> None:
        if self.ws and self.connected:
            try:
                await self.ws.send(data)
            except Exception as e:
                logger.error(f"Send voice error: {e}")

    async def send_voice_message(self, audio_data: str) -> None:
        """发送语音消息 (JSON格式)"""
        if self.ws and self.connected:
            message = {
                "type": "SEND_VOICE",
                "data": audio_data,
                "timestamp": int(asyncio.get_event_loop().time() * 1000)
            }
            try:
                await self.ws.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Send voice message error: {e}")

    async def send_silence(self) -> None:
        if self.ws and self.connected:
            message = {
                "type": "SILENCE",
                "timestamp": int(asyncio.get_event_loop().time() * 1000)
            }
            try:
                await self.ws.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Send silence error: {e}")

    async def send_control(self, action: str, **kwargs) -> None:
        if self.ws and self.connected:
            message = {
                "type": "CONTROL",
                "action": action,
                "timestamp": int(asyncio.get_event_loop().time() * 1000),
                **kwargs
            }
            try:
                await self.ws.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Send control error: {e}")

    async def send_heartbeat(self) -> None:
        if self.ws and self.connected:
            message = {
                "type": "HEARTBEAT",
                "timestamp": int(asyncio.get_event_loop().time() * 1000)
            }
            try:
                await self.ws.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Send heartbeat error: {e}")

    def parse_message(self, message: dict) -> Optional[dict]:
        msg_type = message.get("type", "").upper()
        if msg_type == "VOICE":
            return {
                "type": "VOICE",
                "sender_id": message.get("sender_id", 0),
                "sender_name": message.get("sender_name"),
                "codec_type": message.get("codec_type", "opus"),
                "timestamp": message.get("timestamp", 0),
                "sequence": message.get("sequence", 0),
                "data": message.get("data", ""),
            }
        elif msg_type == "WHISPER":
            return {
                "type": "WHISPER",
                "sender_id": message.get("sender_id", 0),
                "sender_name": message.get("sender_name"),
                "target_id": message.get("target_id"),
                "codec_type": message.get("codec_type", "opus"),
                "timestamp": message.get("timestamp", 0),
                "sequence": message.get("sequence", 0),
                "data": message.get("data", ""),
            }
        elif msg_type == "HEARTBEAT":
            return {"type": "HEARTBEAT", "timestamp": message.get("timestamp", 0)}
        elif msg_type == "CONTROL":
            return {"type": "CONTROL", "action": message.get("action", ""), "data": message.get("data")}
        elif msg_type == "ERROR":
            logger.error(f"TeamSpeak error: {message.get('message', 'Unknown error')}")
            return {"type": "ERROR", "code": message.get("code"), "message": message.get("message")}
        return None


ts_client = TeamSpeakWebSocket()


@router.websocket("/teamspeak")
async def teamspeak_websocket(websocket: WebSocket):
    """TeamSpeak WebSocket 端点 — 纯中继 + AudioBus 发布"""
    await websocket.accept()
    client_active = True
    logger.info("New TeamSpeak WebSocket connection established")

    async def receive_from_frontend():
        """接收前端消息并转发到 TeamSpeak"""
        try:
            while client_active:
                message = await websocket.receive()
                if message["type"] == "websocket.receive":
                    if "text" in message:
                        try:
                            data = json.loads(message["text"])
                            msg_type = data.get("type", "").upper()
                            if msg_type == "CONNECT":
                                url = data.get("url", settings.ts_ws_url)
                                if await ts_client.connect(url):
                                    await websocket.send_json({"type": "CONNECTED", "message": "Connected to TeamSpeak Voice Bridge"})
                                else:
                                    await websocket.send_json({"type": "ERROR", "message": "Failed to connect"})
                            elif msg_type == "DISCONNECT":
                                await ts_client.disconnect()
                                await websocket.send_json({"type": "DISCONNECTED", "message": "Disconnected"})
                            elif msg_type == "SEND_VOICE":
                                await ts_client.send_voice_message(data.get("data", ""))
                            elif msg_type == "SILENCE":
                                await ts_client.send_silence()
                            elif msg_type == "CONTROL":
                                await ts_client.send_control(data.get("action", ""), **data.get("params", {}))
                            elif msg_type == "HEARTBEAT":
                                await ts_client.send_heartbeat()
                        except json.JSONDecodeError:
                            pass
                    elif "bytes" in message:
                        await ts_client.send_voice(message["bytes"])
        except WebSocketDisconnect:
            logger.info("Frontend disconnected")
        except Exception as e:
            logger.error(f"Receive error: {e}")

    async def receive_from_teamspeak():
        """从 TeamSpeak 接收消息 → 中继到前端 + 发布到 AudioBus"""
        try:
            async for message in ts_client.receive_message():
                if not client_active:
                    break
                if isinstance(message, dict):
                    parsed = ts_client.parse_message(message)
                    if parsed:
                        # 中继到前端
                        await websocket.send_json(parsed)

                        msg_type = parsed.get("type")
                        if msg_type in ("VOICE", "WHISPER"):
                            import base64
                            try:
                                frame_data = base64.b64decode(parsed.get("data", ""))
                                # 发布到 AudioBus（供 pipeline stt_listen 节点使用）
                                await audio_bus.publish(frame_data, sender_id=parsed.get("sender_id", 0))
                            except Exception as e:
                                logger.error(f"Failed to decode audio data: {e}")
                else:
                    await websocket.send_bytes(message)
        except Exception as e:
            logger.error(f"TeamSpeak receive error: {e}")
            await websocket.send_json({"type": "ERROR", "message": str(e)})

    async def heartbeat_loop():
        while client_active and ts_client.connected:
            await ts_client.send_heartbeat()
            await asyncio.sleep(25)

    try:
        await asyncio.gather(
            receive_from_frontend(),
            receive_from_teamspeak(),
            heartbeat_loop(),
        )
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        client_active = False
        await ts_client.disconnect()
        logger.info("TeamSpeak WebSocket session ended")


@router.get("/teamspeak/status")
async def get_teamspeak_status():
    return {"connected": ts_client.connected, "reconnect_attempts": ts_client.reconnect_attempts}


@router.post("/teamspeak/connect")
async def connect_teamspeak(url: Optional[str] = None):
    success = await ts_client.connect(url)
    return {"success": success}


@router.post("/teamspeak/disconnect")
async def disconnect_teamspeak():
    await ts_client.disconnect()
    return {"success": True}
