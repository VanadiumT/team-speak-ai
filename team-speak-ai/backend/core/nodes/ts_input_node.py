"""
TS Input 节点 — TeamSpeak 音频输入源

作为 Pipeline 的音频入口，从 AudioBus 订阅 TS 音频流并输出。
"""

import asyncio
import logging

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry
from core.audio.audio_bus import audio_bus

logger = logging.getLogger(__name__)


@NodeRegistry.register("ts_input")
class TSInputNode(BaseNode):
    """TS 音频输入节点"""

    node_type = "ts_input"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        listener_id = f"ts_input_{context.execution_id}_{context.node_id}"
        audio_bus.subscribe(listener_id)

        accumulated_frames = []
        total_bytes = 0
        max_bytes = context.node_config.get("max_buffer_bytes", 10 * 1024 * 1024)

        try:
            await emit.emit_node_update(
                context.node_id,
                "listening",
                "接收 TS 音频流...",
                data={"mode": "receiving"},
            )

            while True:
                frame = await audio_bus.get_audio(listener_id, timeout=0.5)
                if frame is None:
                    continue

                audio_bytes = frame.get("data", b"")
                if not audio_bytes:
                    continue

                accumulated_frames.append(frame)
                total_bytes += len(audio_bytes)

                await emit.emit_node_update(
                    context.node_id,
                    "processing",
                    f"已接收 {total_bytes / 1024:.1f} KB",
                    data={"bytes_received": total_bytes, "frame_count": len(accumulated_frames)},
                )

                # 达到缓冲区上限时输出
                if total_bytes >= max_bytes:
                    break

        except asyncio.CancelledError:
            logger.info(f"TSInput cancelled: {context.node_id}")
            raise
        finally:
            audio_bus.unsubscribe(listener_id)

        await emit.emit_node_update(
            context.node_id,
            "completed",
            f"已接收 {total_bytes / 1024:.1f} KB 音频",
            data={"total_bytes": total_bytes, "frames": len(accumulated_frames)},
        )

        return NodeOutput({
            "audio_frames": accumulated_frames,
            "total_bytes": total_bytes,
        })
