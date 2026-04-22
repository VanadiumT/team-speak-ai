from typing import Dict
from datetime import datetime


class AudioBuffer:
    """管理单个说话者的语音片段缓冲"""

    def __init__(self, timeout: float = 2.0):
        self.timeout = timeout
        self._buffers: Dict[int, dict] = {}

    def add_frame(self, sender_id: int, frame: bytes, sequence: int, timestamp: int):
        """添加音频帧"""
        if sender_id not in self._buffers:
            self._buffers[sender_id] = {
                "frames": [],
                "start_time": datetime.now(),
                "last_sequence": sequence,
                "last_timestamp": timestamp,
            }

        buffer = self._buffers[sender_id]
        buffer["frames"].append(frame)
        buffer["last_sequence"] = sequence
        buffer["last_timestamp"] = timestamp

    def is_complete(self, sender_id: int) -> bool:
        """检查是否完成（空数据或超时）"""
        if sender_id not in self._buffers:
            return False

        buffer = self._buffers[sender_id]
        if not buffer["frames"]:
            return True

        elapsed = (datetime.now() - buffer["start_time"]).total_seconds()
        return elapsed > self.timeout

    def get_audio(self, sender_id: int) -> bytes:
        """获取完整音频数据"""
        if sender_id not in self._buffers:
            return b""

        buffer = self._buffers[sender_id]
        audio_data = b"".join(buffer["frames"])
        return audio_data

    def clear(self, sender_id: int) -> None:
        """清理指定说话者的缓冲"""
        if sender_id in self._buffers:
            del self._buffers[sender_id]
