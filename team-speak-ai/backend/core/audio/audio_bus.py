"""
音频总线 — 发布/订阅模式

ws_teamspeak.py 收到 TS 音频后 publish 到此总线，
pipeline 的 stt_listen 节点通过 subscribe 获取音频数据进行识别。
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AudioBus:
    """音频发布订阅总线"""

    def __init__(self):
        self._queues: dict[str, asyncio.Queue] = {}

    def subscribe(self, listener_id: str, maxsize: int = 100):
        """订阅音频流，返回 asyncio.Queue"""
        if listener_id not in self._queues:
            self._queues[listener_id] = asyncio.Queue(maxsize=maxsize)
            logger.debug(f"AudioBus subscriber added: {listener_id}")
        return self._queues[listener_id]

    def unsubscribe(self, listener_id: str):
        """取消订阅"""
        self._queues.pop(listener_id, None)
        logger.debug(f"AudioBus subscriber removed: {listener_id}")

    async def publish(self, audio_data: bytes, sender_id: int = 0):
        """发布音频数据到所有订阅者"""
        for listener_id, q in list(self._queues.items()):
            try:
                q.put_nowait({"data": audio_data, "sender_id": sender_id})
            except asyncio.QueueFull:
                # 队列满时丢弃旧数据
                try:
                    q.get_nowait()
                    q.put_nowait({"data": audio_data, "sender_id": sender_id})
                except asyncio.QueueEmpty:
                    pass

    async def get_audio(self, listener_id: str, timeout: float = 0.1) -> Optional[dict]:
        """订阅者获取音频数据"""
        q = self._queues.get(listener_id)
        if q is None:
            return None
        try:
            return await asyncio.wait_for(q.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    @property
    def subscriber_count(self) -> int:
        return len(self._queues)


audio_bus = AudioBus()
