"""
VAD 节点 — 语音活动检测 + 分句

从上游节点接收连续 PCM 音频，使用 WebRTC VAD 检测语音活动，
在检测到完整句子后输出分句音频块。
"""

import asyncio
import base64
import logging

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry
from core.audio.audio_buffer import VADBuffer

logger = logging.getLogger(__name__)


@NodeRegistry.register("vad")
class VADNode(BaseNode):
    """VAD 分句节点"""

    node_type = "vad"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        cfg = context.node_config
        logger.info(f"VAD execute start: node={context.node_id}")

        # ── 预设解析 ──
        if cfg.get("platform_id") and cfg.get("model_id"):
            effective = self._resolve_vad_preset_config(cfg)
        else:
            effective = _DEFAULT_VAD_EFFECTIVE

        sample_rate = effective["sample_rate"]

        # ── 获取输入音频 ──
        audio_data = context.inputs.get("stream-audio")
        logger.info(f"VAD audio_data type={type(audio_data).__name__}, len={len(audio_data) if audio_data else 0}")
        if audio_data is None:
            await emit.emit_node_error(context.node_id, "未收到音频数据")
            return NodeOutput({}, trigger_next=False)

        pcm_bytes = _resolve_pcm(audio_data)
        if not pcm_bytes:
            logger.warning(f"VAD _resolve_pcm returned empty, audio_data preview: {str(audio_data)[:200]}")
            await emit.emit_node_error(context.node_id, "无法解析音频数据")
            return NodeOutput({}, trigger_next=False)

        logger.info(f"VAD pcm_bytes={len(pcm_bytes)} bytes, sample_rate={sample_rate}")
        await emit.emit_node_update(
            context.node_id, "processing",
            f"VAD 分句中 (共 {len(pcm_bytes)} 字节)",
            data={"mode": "splitting", "total_bytes": len(pcm_bytes)},
        )

        # ── VAD 分句 ──
        vad = VADBuffer(
            vad_mode=effective["vad_mode"],
            frame_duration_ms=effective["frame_duration_ms"],
            hangover_ms=effective["hangover_ms"],
            min_speech_ms=effective["min_speech_ms"],
            sample_rate=sample_rate,
        )

        frame_size = vad.frame_size_bytes
        chunks = []

        for offset in range(0, len(pcm_bytes), frame_size):
            frame = pcm_bytes[offset:offset + frame_size]
            if len(frame) < frame_size:
                frame = frame + b"\x00" * (frame_size - len(frame))

            vad.add_frame(0, frame)

            if vad.has_complete_sentence(0):
                sentence_pcm = vad.get_complete_sentence(0)
                chunks.append(sentence_pcm)
                await emit.emit_node_update(
                    context.node_id, "processing",
                    f"VAD 分句中 ({len(chunks)} 句)",
                    data={"chunk_index": len(chunks), "chunk_size": len(sentence_pcm)},
                )

        # 冲刷剩余语音
        remainder = vad.flush(0)
        if remainder and len(remainder) >= frame_size * vad.min_speech_frames:
            chunks.append(remainder)

        if not chunks:
            await emit.emit_node_update(
                context.node_id, "completed",
                "未检测到有效语音",
                data={"total_chunks": 0},
            )
            return NodeOutput({
                "chunk-audio": [],
                "total_chunks": 0,
            })

        await emit.emit_node_update(
            context.node_id, "completed",
            f"分句完成 ({len(chunks)} 句)",
            data={"total_chunks": len(chunks)},
        )

        safe_chunks = [base64.b64encode(c).decode("ascii") if isinstance(c, bytes) else c for c in chunks]
        return NodeOutput({
            "chunk-audio": safe_chunks,
            "total_chunks": len(safe_chunks),
        })

    # ── 预设解析 ──

    @staticmethod
    def _resolve_vad_preset_config(cfg: dict) -> dict:
        from core.app_context import get_app_context
        pm = get_app_context().vad_preset_manager
        return BaseNode._resolve_preset_with_fallback(cfg, pm, fallback_default=_DEFAULT_VAD_EFFECTIVE)


# ── Hardcoded fallback when no presets exist ──
_DEFAULT_VAD_EFFECTIVE = {
    "provider": "webrtcvad",
    "vad_mode": 3,
    "frame_duration_ms": 20,
    "hangover_ms": 600,
    "sample_rate": 16000,
    "min_speech_ms": 300,
}


def _resolve_pcm(audio_data) -> bytes:
    """将各种输入格式统一解析为 PCM bytes"""
    if isinstance(audio_data, (bytes, bytearray)):
        return bytes(audio_data)
    if isinstance(audio_data, dict):
        # ts_input 输出: {"audio": [...], "total_bytes": ...}
        frames = audio_data.get("audio") or audio_data.get("audio_frames", [])
        if frames:
            return b"".join(f.get("data", b"") if isinstance(f, dict) else bytes(f) for f in frames)
        # 可能直接是 pcm data
        if "data" in audio_data:
            return _resolve_pcm(audio_data["data"])
    if isinstance(audio_data, list):
        return b"".join(_resolve_pcm(item) for item in audio_data)
    if isinstance(audio_data, str):
        try:
            return base64.b64decode(audio_data)
        except Exception:
            pass
    return b""
