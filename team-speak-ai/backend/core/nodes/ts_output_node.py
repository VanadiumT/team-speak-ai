"""
TS Output 节点 — 将音频输出到 TeamSpeak

接收 TTS 节点的音频数据，通过 ws_teamspeak 的 TeamSpeakWebSocket
发送 SEND_VOICE 消息到 TeamSpeak Voice Bridge，在频道内播放。
"""

import base64
import logging

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry

logger = logging.getLogger(__name__)


@NodeRegistry.register("ts_output")
class TSOutputNode(BaseNode):
    """TeamSpeak 音频输出节点"""

    node_type = "ts_output"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        audio_b64 = context.inputs.get("audio_b64", "")
        text = context.inputs.get("text", "")

        if not audio_b64:
            await emit.emit_node_update(context.node_id, "completed", "无音频数据")
            return NodeOutput({"sent": False, "reason": "no_audio"})

        await emit.emit_node_update(
            context.node_id,
            "processing",
            "正在发送到 TeamSpeak...",
        )

        try:
            # 通过 ws_teamspeak 发送到 TeamSpeak
            from api.routes.ws_teamspeak import ts_client
            if ts_client and ts_client.connected:
                await ts_client.send_voice_message(audio_b64)
                logger.info(f"Audio sent to TeamSpeak ({len(audio_b64)} chars base64)")
                await emit.emit_node_update(
                    context.node_id,
                    "completed",
                    f"已发送到 TeamSpeak",
                    data={"sent": True, "text_preview": text[:60] if text else ""},
                )
                return NodeOutput({"sent": True})
            else:
                logger.warning("TeamSpeak not connected, cannot send audio")
                await emit.emit_node_update(
                    context.node_id,
                    "error",
                    "TeamSpeak 未连接",
                )
                return NodeOutput({"sent": False, "reason": "not_connected"}, trigger_next=False)

        except Exception as e:
            logger.exception(f"TS output error")
            await emit.emit_node_error(context.node_id, str(e))
            return NodeOutput({"sent": False, "reason": str(e)}, trigger_next=False)
