"""
VAD 音频缓冲 — 基于 WebRTC VAD 的逐帧语音活动检测 + 分句

每帧 PCM 通过 webrtcvad 判断有声/静音，通过 hangover 逻辑
在检测到完整句子后自动切分输出。
"""

import logging
import webrtcvad
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class VADBuffer:
    """WebRTC VAD 驱动的音频分句缓冲器"""

    def __init__(
        self,
        vad_mode: int = 3,
        frame_duration_ms: int = 20,
        hangover_ms: int = 600,
        min_speech_ms: int = 300,
        sample_rate: int = 16000,
    ):
        if sample_rate not in (8000, 16000, 32000, 48000):
            raise ValueError(f"webrtcvad only supports 8000/16000/32000/48000 Hz, got {sample_rate}")
        if frame_duration_ms not in (10, 20, 30):
            raise ValueError(f"frame_duration_ms must be 10, 20, or 30, got {frame_duration_ms}")

        self._vad = webrtcvad.Vad(vad_mode)
        self._sample_rate = sample_rate
        self._frame_duration_ms = frame_duration_ms
        self._hangover_frames = max(1, int(hangover_ms / frame_duration_ms))
        self._min_speech_frames = max(1, int(min_speech_ms / frame_duration_ms))

        # 16-bit mono PCM: sample_rate * 2 bytes/sample * duration_seconds
        self._frame_size_bytes = int(sample_rate * 2 * frame_duration_ms / 1000)

        # per-sender state
        self._senders: Dict[int, dict] = {}

    @property
    def frame_size_bytes(self) -> int:
        return self._frame_size_bytes

    @property
    def min_speech_frames(self) -> int:
        return self._min_speech_frames

    def add_frame(self, sender_id: int, frame: bytes) -> None:
        """喂入一帧 PCM 数据 (16-bit mono)，长度必须等于 frame_size_bytes"""
        if len(frame) != self._frame_size_bytes:
            logger.debug(f"VAD frame size mismatch: got {len(frame)}, expected {self._frame_size_bytes}")
            return

        state = self._senders.setdefault(sender_id, {
            "frames": [],
            "voiced_count": 0,
            "silence_count": 0,
            "done": False,
        })

        if state["done"]:
            return

        is_speech = self._vad.is_speech(frame, self._sample_rate)

        if is_speech:
            state["frames"].append(frame)
            state["voiced_count"] += 1
            state["silence_count"] = 0
        else:
            # 只有已经开始说话后才计静音帧
            if state["voiced_count"] > 0:
                state["frames"].append(frame)
                state["silence_count"] += 1

            if (state["silence_count"] >= self._hangover_frames
                    and state["voiced_count"] >= self._min_speech_frames):
                state["done"] = True

    def has_complete_sentence(self, sender_id: int) -> bool:
        state = self._senders.get(sender_id)
        return bool(state and state["done"])

    def get_complete_sentence(self, sender_id: int) -> Optional[bytes]:
        """取出完整句子的 PCM 数据，同时清理该 sender 状态"""
        state = self._senders.pop(sender_id, None)
        if not state or not state["done"]:
            return None
        return b"".join(state["frames"])

    def flush(self, sender_id: int) -> Optional[bytes]:
        """强制输出当前缓冲中的语音（即使 hangover 没到）"""
        state = self._senders.pop(sender_id, None)
        if not state or not state["frames"]:
            return None
        return b"".join(state["frames"])

    def clear(self, sender_id: int) -> None:
        self._senders.pop(sender_id, None)
