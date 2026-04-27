"""
TS Output 节点 — 逐段发送音频到 TeamSpeak

接收 TTS 节点输出的 segments 数组，逐段通过 ts_client 发送到 TeamSpeak，
每段之间间隔 0.2s 防止拥塞。
"""

import asyncio
import logging

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry

logger = logging.getLogger(__name__)


@NodeRegistry.register("ts_output")
class TSOutputNode(BaseNode):
    """TeamSpeak 音频输出节点（逐段播放）"""

    node_type = "ts_output"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        segments = context.inputs.get("segments", [])
        if not segments:
            await emit.emit_node_update(context.node_id, "completed", "无音频数据")
            return NodeOutput({"sent": False, "reason": "no_segments"})

        # 通过 ws_teamspeak 发送到 TeamSpeak
        from api.routes.ws_teamspeak import ts_client
        if not ts_client or not ts_client.connected:
            logger.warning("TeamSpeak not connected, cannot send audio")
            await emit.emit_node_update(context.node_id, "error", "TeamSpeak 未连接")
            return NodeOutput({"sent": False, "reason": "not_connected"}, trigger_next=False)

        await emit.emit_node_update(
            context.node_id, "processing",
            f"TS 播放中 (0/{len(segments)})",
        )

        sent_count = 0
        for seg in segments:
            audio_b64 = seg.get("audio_b64", "")
            if not audio_b64:
                continue

            try:
                await ts_client.send_voice_message(audio_b64)
                sent_count += 1

                await emit.emit_node_update(
                    context.node_id, "processing",
                    f"TS 播放中 ({sent_count}/{len(segments)})",
                    data={"sent_index": seg.get("index"), "segment_text": seg.get("text", "")},
                )

                await asyncio.sleep(0.2)  # 句间间隔
            except Exception as e:
                logger.exception(f"TS output error")
                await emit.emit_node_error(context.node_id, str(e))
                return NodeOutput({"sent": False, "reason": str(e), "sent_count": sent_count}, trigger_next=False)

        await emit.emit_node_update(context.node_id, "completed", f"已发送 {sent_count} 段到 TeamSpeak")
        return NodeOutput({"sent": True, "segment_count": sent_count})
