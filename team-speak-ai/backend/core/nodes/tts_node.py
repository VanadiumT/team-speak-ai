"""
TTS 节点 — 文本转语音

将 LLM 输出的文本合成为音频数据。
"""

import logging
from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry
from core.tts.factory import TTSProvider, create_tts
from config import settings

logger = logging.getLogger(__name__)


@NodeRegistry.register("tts")
class TTSNode(BaseNode):
    """语音合成节点"""

    node_type = "tts"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        text = context.inputs.get("response", context.inputs.get("text", ""))

        if not text or len(text.strip()) == 0:
            await emit.emit_node_update(context.node_id, "completed", "无文本可合成")
            return NodeOutput({"audio": b"", "format": ""})

        await emit.emit_node_update(
            context.node_id,
            "processing",
            f"正在合成语音 ({len(text)} 字)...",
        )

        try:
            tts = self._get_tts()
            audio_bytes = await tts.synthesize(text)

            import base64
            audio_b64 = base64.b64encode(audio_bytes).decode()

            await emit.emit_node_update(
                context.node_id,
                "completed",
                f"合成完成 ({len(audio_bytes)} bytes)",
                data={"audio_size": len(audio_bytes)},
            )

            return NodeOutput({
                "audio": audio_bytes,
                "audio_b64": audio_b64,
                "format": "mp3",
                "text": text,
            })

        except Exception as e:
            logger.exception(f"TTS error")
            await emit.emit_node_error(context.node_id, str(e))
            return NodeOutput({"audio": b"", "format": "", "error": str(e)}, trigger_next=False)

    @staticmethod
    def _get_tts():
        provider = TTSProvider(settings.tts_provider)
        tts_config = {
            "edge": {"voice": getattr(settings, "edge_voice", "zh-CN-XiaoxiaoNeural")},
            "minimax": {
                "api_key": settings.minimax_api_key,
                "model": settings.minimax_tts_model,
                "voice_id": settings.minimax_voice_id,
                "speed": settings.minimax_speed,
                "vol": settings.minimax_vol,
            },
        }
        config = tts_config.get(settings.tts_provider, tts_config["edge"])
        return create_tts(provider, config)
