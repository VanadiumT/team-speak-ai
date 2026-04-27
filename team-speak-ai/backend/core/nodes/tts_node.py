"""
TTS 节点 — 文本转语音（逐句合成）

将输入的文本按句子分割，逐句合成音频，
返回 segments 数组供 TSOutputNode 逐段播放。
"""

import re
import base64
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
    """语音合成节点（逐句合成）"""

    node_type = "tts"

    def _split_sentences(self, text: str) -> list[str]:
        """按句子边界分割文本"""
        parts = re.split(r'(?<=[。！？.!?\n])', text)
        return [p.strip() for p in parts if p.strip()]

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        text = context.inputs.get("response", context.inputs.get("text", ""))

        if not text or len(text.strip()) == 0:
            await emit.emit_node_update(context.node_id, "completed", "无文本可合成")
            return NodeOutput({"segments": [], "text": ""})

        tts = self._get_tts()
        sentences = self._split_sentences(text)
        segments = []

        await emit.emit_node_update(
            context.node_id, "processing",
            f"语音合成中 (0/{len(sentences)})",
            data={"mode": "synthesizing", "total": len(sentences)},
        )

        try:
            for i, sentence in enumerate(sentences):
                audio_bytes = await tts.synthesize(sentence)
                audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
                segments.append({
                    "text": sentence,
                    "audio_b64": audio_b64,
                    "index": i,
                })
                await emit.emit_node_update(
                    context.node_id, "processing",
                    f"语音合成中 ({i+1}/{len(sentences)})",
                    data={
                        "segment_index": i,
                        "segment_text": sentence,
                        "audio_b64": audio_b64,
                    },
                )

            return NodeOutput({
                "segments": segments,
                "text": text,
                "total_segments": len(segments),
            })

        except Exception as e:
            logger.exception(f"TTS error")
            await emit.emit_node_error(context.node_id, str(e))
            return NodeOutput({"segments": [], "text": ""}, trigger_next=False)

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
