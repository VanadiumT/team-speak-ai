"""
TS Output 节点 — 流式 / 非流式音频发送到 TeamSpeak

支持 execute_stream（流式）和 execute（非流式）两条路径，
通过 ts_client 逐段或一次性将音频发送到 TeamSpeak。
"""

import asyncio
import logging
from typing import AsyncGenerator

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput, _STREAM_END
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry

logger = logging.getLogger(__name__)


@NodeRegistry.register("ts_output")
class TSOutputNode(BaseNode):
    """TeamSpeak 音频输出节点（流式 / 非流式）"""

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
        await emit.emit_node_update(context.node_id, "processing", f"{label}中 (1/1)")

        try:
            await ts_client.send_voice_message(audio_b64)
        except Exception as e:
            logger.exception("TS output error")
            await emit.emit_node_error(context.node_id, str(e))
            return NodeOutput({"sent": False, "reason": str(e)}, trigger_next=False)

        summary = "已发送 1 段到 TeamSpeak" if connected else "已回环 1 段到 AudioBus"
        await emit.emit_node_update(context.node_id, "completed", summary)
        return NodeOutput({"sent": True, "segment_count": 1})

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
        index = 0
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
                try:
                    await ts_client.send_voice_message(audio_b64)
                except Exception as e:
                    logger.exception("TS output streaming error")
                    await emit.emit_node_error(context.node_id, str(e))
                    yield NodeOutput({"sent": False, "reason": str(e), "segment_count": index}, final=True)
                    return

            await emit.emit_node_update(
                context.node_id, "processing",
                f"{label}中 ({index + 1})",
                data={"segment_index": index, "segment_text": seg_text},
            )

            yield NodeOutput(
                data={"sent_index": index, "segment_text": seg_text},
                final=False,
            )

            await asyncio.sleep(0.2)
            index += 1

        summary = f"已发送 {index} 段到 TeamSpeak" if connected else f"已回环 {index} 段到 AudioBus"
        await emit.emit_node_update(context.node_id, "completed", summary)
        yield NodeOutput({"sent": True, "segment_count": index}, final=True)


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
