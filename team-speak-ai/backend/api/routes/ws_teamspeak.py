import json
import asyncio
import logging
from typing import Optional, AsyncIterator
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime
import uuid

from config import settings
from core.audio.audio_buffer import AudioBuffer
from core.stt.factory import STTProvider, create_stt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["teamspeak"])

# 全局音频缓冲
audio_buffer = AudioBuffer()

# STT 实例
_stt_instance = None


def get_stt_instance():
    """获取或创建 STT 实例"""
    global _stt_instance
    if _stt_instance is None:
        provider = STTProvider(settings.stt_provider)
        stt_config = {
            "whisper": {
                "model_name": settings.whisper_model,
                "device": settings.whisper_device,
            },
            "minimax": {
                "api_key": settings.minimax_api_key,
                "api_url": settings.minimax_api_url,
            },
            "sensevoice": {
                "model_dir": settings.sensevoice_model,
                "device": settings.sensevoice_device,
            },
        }
        config = stt_config.get(settings.stt_provider, stt_config["whisper"])
        _stt_instance = create_stt(provider, config)
        logger.info(f"STT instance created: {settings.stt_provider}")
    return _stt_instance


class TeamSpeakWebSocket:
    """TeamSpeak WebSocket 客户端"""

    def __init__(self):
        self.ws: Optional[WebSocket] = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self._should_reconnect = True

    async def connect(self, url: str = None) -> bool:
        """建立连接"""
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
        """断开连接"""
        self._should_reconnect = False
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.connected = False
            logger.info("Disconnected from TeamSpeak WebSocket")

    async def reconnect(self, url: str = None) -> bool:
        """尝试重连"""
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
        """接收消息"""
        if not self.ws:
            return

        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    yield data
                except json.JSONDecodeError:
                    # 二进制音频数据
                    yield {"type": "BINARY", "data": message}
        except Exception as e:
            logger.error(f"Receive error: {e}")

    async def send_voice(self, data: bytes) -> None:
        """发送语音数据"""
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
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
            try:
                await self.ws.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Send voice message error: {e}")

    async def send_silence(self) -> None:
        """发送静音（结束说话）"""
        if self.ws and self.connected:
            message = {
                "type": "SILENCE",
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
            try:
                await self.ws.send(json.dumps(message))
                logger.debug("Sent silence signal")
            except Exception as e:
                logger.error(f"Send silence error: {e}")

    async def send_control(self, action: str, **kwargs) -> None:
        """发送控制命令"""
        if self.ws and self.connected:
            message = {
                "type": "CONTROL",
                "action": action,
                "timestamp": int(datetime.now().timestamp() * 1000),
                **kwargs
            }
            try:
                await self.ws.send(json.dumps(message))
                logger.debug(f"Sent control command: {action}")
            except Exception as e:
                logger.error(f"Send control error: {e}")

    async def send_heartbeat(self) -> None:
        """发送心跳"""
        if self.ws and self.connected:
            message = {
                "type": "HEARTBEAT",
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
            try:
                await self.ws.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Send heartbeat error: {e}")

    def parse_message(self, message: dict) -> Optional[dict]:
        """解析消息，返回标准化格式"""
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
            return {
                "type": "HEARTBEAT",
                "timestamp": message.get("timestamp", 0),
            }

        elif msg_type == "CONTROL":
            return {
                "type": "CONTROL",
                "action": message.get("action", ""),
                "data": message.get("data"),
            }

        elif msg_type == "ERROR":
            logger.error(f"TeamSpeak error: {message.get('message', 'Unknown error')}")
            return {
                "type": "ERROR",
                "code": message.get("code"),
                "message": message.get("message"),
            }

        return None


# 全局客户端实例
ts_client = TeamSpeakWebSocket()


@router.websocket("/teamspeak")
async def teamspeak_websocket(websocket: WebSocket):
    """TeamSpeak WebSocket 端点 - 桥接前端与TeamSpeak Voice Bridge"""
    await websocket.accept()
    client_active = True

    logger.info("New TeamSpeak WebSocket connection established")

    async def receive_from_frontend():
        """接收前端消息并转发到TeamSpeak"""
        try:
            while client_active:
                message = await websocket.receive()
                if message["type"] == "websocket.receive":
                    # 处理文本消息
                    if "text" in message:
                        try:
                            data = json.loads(message["text"])
                            msg_type = data.get("type", "").upper()

                            if msg_type == "CONNECT":
                                # 前端请求连接
                                url = data.get("url", settings.ts_ws_url)
                                if await ts_client.connect(url):
                                    await websocket.send_json({
                                        "type": "CONNECTED",
                                        "message": "Connected to TeamSpeak Voice Bridge"
                                    })
                                else:
                                    await websocket.send_json({
                                        "type": "ERROR",
                                        "message": "Failed to connect"
                                    })

                            elif msg_type == "DISCONNECT":
                                await ts_client.disconnect()
                                await websocket.send_json({
                                    "type": "DISCONNECTED",
                                    "message": "Disconnected"
                                })

                            elif msg_type == "SEND_VOICE":
                                await ts_client.send_voice_message(data.get("data", ""))

                            elif msg_type == "SILENCE":
                                await ts_client.send_silence()

                            elif msg_type == "CONTROL":
                                await ts_client.send_control(
                                    data.get("action", ""),
                                    **data.get("params", {})
                                )

                            elif msg_type == "HEARTBEAT":
                                await ts_client.send_heartbeat()

                        except json.JSONDecodeError:
                            pass

                    # 处理二进制消息
                    elif "bytes" in message:
                        await ts_client.send_voice(message["bytes"])

        except WebSocketDisconnect:
            logger.info("Frontend disconnected")
        except Exception as e:
            logger.error(f"Receive error: {e}")

    async def process_complete_audio(sender_id: int, sender_name: Optional[str], timestamp: int):
        """处理已完成的音频片段 - 执行 STT 并广播结果"""
        audio_data = audio_buffer.get_audio(sender_id)
        if not audio_data:
            return

        request_id = str(uuid.uuid4())
        start_time = datetime.now()

        try:
            stt = get_stt_instance()
            text = await stt.transcribe(audio_data)
            duration = (datetime.now() - start_time).total_seconds()

            if text:
                logger.info(f"STT result for user {sender_id}: {text[:50]}...")
                # 广播到所有客户端
                from api.routes.ws_client import broadcast_teamspeak_event
                await broadcast_teamspeak_event("stt_result", {
                    "request_id": request_id,
                    "sender_id": sender_id,
                    "sender_name": sender_name,
                    "text": text,
                    "duration": duration,
                    "timestamp": timestamp,
                })
            else:
                logger.debug(f"STT returned empty text for user {sender_id}")

        except Exception as e:
            logger.error(f"STT processing error for user {sender_id}: {e}")
        finally:
            audio_buffer.clear(sender_id)

    async def receive_from_teamspeak():
        """从TeamSpeak接收消息并转发到前端"""
        try:
            async for message in ts_client.receive_message():
                if not client_active:
                    break

                if isinstance(message, dict):
                    parsed = ts_client.parse_message(message)
                    if parsed:
                        await websocket.send_json(parsed)

                        # 记录日志
                        msg_type = parsed.get("type")
                        if msg_type == "VOICE":
                            logger.info(f"Received VOICE from user {parsed.get('sender_id')}: "
                                        f"seq={parsed.get('sequence')}, "
                                        f"data_size={len(parsed.get('data', ''))} bytes")
                        elif msg_type == "WHISPER":
                            logger.info(f"Received WHISPER from user {parsed.get('sender_id')}: "
                                        f"target={parsed.get('target_id')}")
                        elif msg_type == "HEARTBEAT":
                            logger.debug(f"Received HEARTBEAT")

                        # 添加到音频缓冲
                        if msg_type in ("VOICE", "WHISPER"):
                            import base64
                            try:
                                frame_data = base64.b64decode(parsed.get("data", ""))
                                audio_buffer.add_frame(
                                    sender_id=parsed.get("sender_id", 0),
                                    frame=frame_data,
                                    sequence=parsed.get("sequence", 0),
                                    timestamp=parsed.get("timestamp", 0),
                                )

                                # 检查是否完成 (通过检查 buffer 中是否有数据且超时时)
                                # 简单检查：如果当前帧数据较小，可能表示说话结束
                                if len(frame_data) < 1000 and audio_buffer.is_complete(parsed.get("sender_id", 0)):
                                    await process_complete_audio(
                                        sender_id=parsed.get("sender_id", 0),
                                        sender_name=parsed.get("sender_name"),
                                        timestamp=parsed.get("timestamp", 0),
                                    )
                            except Exception as e:
                                logger.error(f"Failed to decode audio data: {e}")
                else:
                    # 二进制数据
                    await websocket.send_bytes(message)

        except Exception as e:
            logger.error(f"TeamSpeak receive error: {e}")
            await websocket.send_json({
                "type": "ERROR",
                "message": str(e)
            })

    async def heartbeat_loop():
        """心跳循环"""
        while client_active and ts_client.connected:
            await ts_client.send_heartbeat()
            await asyncio.sleep(25)  # 每25秒发送一次心跳

    # 并行运行接收和心跳
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
    """获取TeamSpeak连接状态"""
    return {
        "connected": ts_client.connected,
        "reconnect_attempts": ts_client.reconnect_attempts,
    }


@router.post("/teamspeak/connect")
async def connect_teamspeak(url: Optional[str] = None):
    """主动连接TeamSpeak Voice Bridge"""
    success = await ts_client.connect(url)
    return {
        "success": success,
        "url": ts_client.ws.remote_address if success else None
    }


@router.post("/teamspeak/disconnect")
async def disconnect_teamspeak():
    """断开TeamSpeak连接"""
    await ts_client.disconnect()
    return {"success": True}
