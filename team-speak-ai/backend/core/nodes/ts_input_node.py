"""
TS Input 节点 — TeamSpeak 音频输入源

作为 Pipeline 的音频入口，从 AudioBus 订阅 TS 音频流并输出。
"""

import asyncio
import base64
import logging
import time

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
        self.node_id = context.node_id
        from api.routes.ws_teamspeak import ts_client

        listener_id = f"ts_input_{context.execution_id}_{context.node_id}"
        try:
            audio_bus.subscribe(listener_id)
        except Exception as e:
            raise self._wrap_error("AudioBus subscribe failed", e) from e

        loopback = context.node_config.get("loopback", False)
        if loopback:
            ts_client.loopback_enabled = True
            self._log_info("loopback enabled")

        accumulated_frames = []
        total_bytes = 0
        max_bytes = context.node_config.get("max_buffer_bytes", 10 * 1024 * 1024)
        silence_timeout = 2.0 if loopback else 0
        last_audio_time = None
        has_any_audio = False

        try:
            self._log_info("接收 TS 音频流..." + (" (含回环监听)" if loopback else ""))
            await emit.emit_node_update(
                context.node_id,
                "listening",
                "接收 TS 音频流..." + (" (含回环监听)" if loopback else ""),
                data={"mode": "receiving", "loopback": loopback},
            )

            while True:
                frame = await audio_bus.get_audio(listener_id, timeout=0.5)
                if frame is None:
                    if silence_timeout > 0 and has_any_audio and last_audio_time:
                        if time.time() - last_audio_time >= silence_timeout:
                            break
                    continue

                audio_bytes = frame.get("data", b"")
                if not audio_bytes:
                    continue

                accumulated_frames.append(frame)
                total_bytes += len(audio_bytes)
                has_any_audio = True
                last_audio_time = time.time()

                await emit.emit_node_update(
                    context.node_id,
                    "processing",
                    f"已接收 {total_bytes / 1024:.1f} KB",
                    data={"bytes_received": total_bytes, "frame_count": len(accumulated_frames)},
                )

                if total_bytes >= max_bytes:
                    break

        except asyncio.CancelledError:
            self._log_info("cancelled")
            audio_bus.unsubscribe(listener_id)
            if loopback:
                ts_client.loopback_enabled = False
                self._log_info("loopback disabled")
            raise

        self._log_info(f"已接收 {total_bytes / 1024:.1f} KB 音频")
        await emit.emit_node_update(
            context.node_id,
            "completed",
            f"已接收 {total_bytes / 1024:.1f} KB 音频",
            data={"total_bytes": total_bytes, "frames": len(accumulated_frames)},
        )

        # Base64-encode frame data for JSON serialization
        safe_frames = []
        for f in accumulated_frames:
            d = dict(f)
            if isinstance(d.get("data"), bytes):
                d["data"] = base64.b64encode(d["data"]).decode("ascii")
            safe_frames.append(d)

        self._log_info(f"returning: frames={len(safe_frames)}, total_bytes={total_bytes}")
        return NodeOutput({
            "audio": safe_frames,
            "total_bytes": total_bytes,
        })
