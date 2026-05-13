"""
TS Output 节点 — 流式 / 非流式音频发送到 TeamSpeak

支持 execute_stream（流式）和 execute（非流式）两条路径。
无论上游输出多大，ts_output 都会将音频切分为小段（~200ms），
逐段发送到 Java 桥接端，确保每帧不超过 WebSocket 消息上限。
"""

import asyncio
import base64
import io
import logging
from typing import AsyncGenerator

import soundfile as sf

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput, _STREAM_END
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry

logger = logging.getLogger(__name__)

# 每段 WebSocket 文本消息目标上限（远小于 Java 端 65KB 默认限制）
_MAX_CHUNK_RAW_BYTES = 24576  # 24KB raw ≈ 32KB base64
_CHUNK_DURATION_MS = 200


@NodeRegistry.register("ts_output")
class TSOutputNode(BaseNode):
    """TeamSpeak 音频输出节点（流式 / 非流式 + 自动分片）"""

    node_type = "ts_output"

    # ── 非流式路径 ──

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        from api.routes.ws_teamspeak import ts_client

        audio_b64 = _extract_b64_from_inputs(context.inputs)
        if not audio_b64:
            await emit.emit_node_update(context.node_id, "completed", "无音频数据")
            return NodeOutput({"sent": False, "reason": "no_audio"})

        connected = ts_client and ts_client.connected
        if not connected and not ts_client.loopback_enabled:
            await emit.emit_node_update(context.node_id, "error", "TeamSpeak 未连接且未开启回环")
            return NodeOutput({"sent": False, "reason": "not_connected"}, trigger_next=False)

        label = "TS 播放" if connected else "回环"
        chunks = _chunk_audio_b64(audio_b64)
        total = len(chunks)

        await emit.emit_node_update(context.node_id, "processing", f"{label}中 (0/{total})",
                                    data={"total_chunks": total})

        for i, chunk_b64 in enumerate(chunks):
            try:
                await ts_client.send_voice_message(chunk_b64)
            except Exception as e:
                logger.exception("TS output error")
                await emit.emit_node_error(context.node_id, str(e))
                return NodeOutput({"sent": False, "reason": str(e), "chunk_index": i}, trigger_next=False)

            await emit.emit_node_update(
                context.node_id, "processing",
                f"{label}中 ({i + 1}/{total})",
                data={"chunk_index": i, "total_chunks": total},
            )

            if total > 1:
                await asyncio.sleep(0.15)

        summary = f"已发送 {total} 段到 TeamSpeak" if connected else f"已回环 {total} 段到 AudioBus"
        await emit.emit_node_update(context.node_id, "completed", summary)
        return NodeOutput({"sent": True, "segment_count": total})

    # ── 流式路径 ──

    async def execute_stream(self, context: NodeContext, emit: EventEmitter) -> AsyncGenerator[NodeOutput, None]:
        if context.stream_input is None:
            output = await self.execute(context, emit)
            yield output
            return

        from api.routes.ws_teamspeak import ts_client

        connected = ts_client and ts_client.connected
        if not connected and not ts_client.loopback_enabled:
            await emit.emit_node_update(context.node_id, "error", "TeamSpeak 未连接且未开启回环")
            yield NodeOutput({"sent": False, "reason": "not_connected"}, final=True)
            return

        label = "TS 播放" if connected else "回环"
        segment_index = 0
        total_chunks = 0

        while True:
            chunk = await context.stream_input.get()
            if chunk is _STREAM_END:
                break
            if chunk is None:
                continue

            audio_b64 = ""
            seg_text = ""
            if isinstance(chunk, NodeOutput) and chunk.data:
                audio_b64 = chunk.data.get("audio_b64", "")
                seg_text = chunk.data.get("text", "")

            if audio_b64:
                sub_chunks = _chunk_audio_b64(audio_b64)
                for sub_b64 in sub_chunks:
                    try:
                        await ts_client.send_voice_message(sub_b64)
                    except Exception as e:
                        logger.exception("TS output streaming error")
                        await emit.emit_node_error(context.node_id, str(e))
                        yield NodeOutput({"sent": False, "reason": str(e), "segment_count": total_chunks}, final=True)
                        return
                    total_chunks += 1
                    if len(sub_chunks) > 1:
                        await asyncio.sleep(0.1)

            await emit.emit_node_update(
                context.node_id, "processing",
                f"{label}中 ({segment_index + 1})",
                data={"segment_index": segment_index, "segment_text": seg_text, "total_chunks": total_chunks},
            )

            yield NodeOutput(
                data={"sent_index": segment_index, "segment_text": seg_text},
                final=False,
            )
            segment_index += 1

        summary = f"已发送 {total_chunks} 段到 TeamSpeak" if connected else f"已回环 {total_chunks} 段到 AudioBus"
        await emit.emit_node_update(context.node_id, "completed", summary)
        yield NodeOutput({"sent": True, "segment_count": total_chunks}, final=True)


# ── helpers ──

def _extract_b64_from_inputs(inputs: dict) -> str:
    """从 inputs 提取音频 base64，优先 batch 再 stream 完整列表"""
    batch = inputs.get("batch-audio", None)
    if isinstance(batch, dict):
        return batch.get("audio_b64", "")
    if isinstance(batch, str):
        return batch

    segments = inputs.get("stream-audio", []) or []
    if isinstance(segments, str):
        return segments
    if isinstance(segments, list) and segments:
        return "".join(
            s.get("audio_b64", "") if isinstance(s, dict) else ""
            for s in segments
        )
    return ""


def _chunk_audio_b64(audio_b64: str, max_raw_bytes: int = _MAX_CHUNK_RAW_BYTES) -> list[str]:
    """将大段 base64 WAV 音频切分为多个独立可播放的小段 base64 WAV。

    每段目标不超过 max_raw_bytes（解码后字节数），以保证 base64 编码后
    的 JSON 消息不超过 Java WebSocket 的 maxTextMessageSize。
    """
    raw = base64.b64decode(audio_b64)
    if len(raw) <= max_raw_bytes:
        return [audio_b64]

    try:
        data, sample_rate = sf.read(io.BytesIO(raw))
    except Exception:
        logger.warning("Chunk: sf.read failed, fallback to raw split")
        return _fallback_raw_split(audio_b64, max_raw_bytes)

    chunk_samples = int(sample_rate * _CHUNK_DURATION_MS / 1000)
    if chunk_samples < 1:
        chunk_samples = len(data)

    chunks = []
    for start in range(0, len(data), chunk_samples):
        segment = data[start:start + chunk_samples]
        buf = io.BytesIO()
        sf.write(buf, segment, sample_rate, format='WAV')
        chunk_b64 = base64.b64encode(buf.getvalue()).decode()
        chunks.append(chunk_b64)

    return chunks


def _fallback_raw_split(audio_b64: str, max_raw_bytes: int) -> list[str]:
    """无法解析音频格式时，按原始 base64 安全切分"""
    chunk_size = int(max_raw_bytes * 0.75)  # base64 overhead ~33%
    return [audio_b64[i:i + chunk_size] for i in range(0, len(audio_b64), chunk_size)]
