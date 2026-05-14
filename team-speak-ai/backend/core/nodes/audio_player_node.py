"""
AudioPlayer 节点 — 音频播放与透传

支持流式（execute_stream）和非流式（execute）两种路径：
- 流式：从 context.stream_input 逐 chunk 读取上游 producer 产出，emit 到前端播放，透传
- 非流式：从 context.inputs 读取完整音频，一次性 emit 到前端，透传
"""

import logging
from typing import AsyncGenerator

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput, NodeState, _STREAM_END
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry

logger = logging.getLogger(__name__)


@NodeRegistry.register("audio_player")
class AudioPlayerNode(BaseNode):
    """音频播放节点（流式 / 非流式 + 透传）"""

    node_type = "audio_player"

    # ── 非流式路径 ──

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        self.node_id = context.node_id
        audio_b64 = _extract_b64_from_inputs(context.inputs)
        if not audio_b64:
            self._log_info("无音频数据")
            await emit.emit_node_update(context.node_id, NodeState.COMPLETED, "无音频数据")
            return NodeOutput({
                "stream-audio": None,
                "batch-audio": None,
                "played": False,
                "reason": "no_audio",
            })

        data_size = len(audio_b64)
        fmt = _audio_format(context.inputs)

        self._log_info("播放中 (1/1)")
        await emit.emit_node_update(
            context.node_id, "processing",
            "播放中 (1/1)",
            data={"mode": "batch", "audio_b64": audio_b64, "format": fmt, "size": data_size},
        )

        await emit.emit_node_update(
            context.node_id, "completed",
            "播放完成",
            data={"mode": "batch", "audio_b64": audio_b64, "format": fmt, "size": data_size},
        )

        return NodeOutput({
            "stream-audio": None,
            "batch-audio": {"audio_b64": audio_b64, "format": fmt},
            "played": True,
            "mode": "batch",
            "size": data_size,
        })

    # ── 流式路径 ──

    async def execute_stream(self, context: NodeContext, emit: EventEmitter) -> AsyncGenerator[NodeOutput, None]:
        if context.stream_input is None:
            output = await self.execute(context, emit)
            yield output
            return

        collected = []
        index = 0

        while True:
            chunk = await context.stream_input.get()
            if chunk is _STREAM_END:
                break
            if chunk is None:
                continue

            # chunk 是上游 producer yield 的 NodeOutput
            audio_b64 = ""
            seg_text = ""
            if isinstance(chunk, NodeOutput) and chunk.data:
                audio_b64 = chunk.data.get("audio_b64", "")
                seg_text = chunk.data.get("text", "")

            collected.append({"audio_b64": audio_b64, "text": seg_text, "index": index})

            await emit.emit_node_update(
                context.node_id, "processing",
                f"播放中 ({index + 1})",
                data={
                    "mode": "stream",
                    "segments": [{"audio_b64": audio_b64, "text": seg_text, "index": index}],
                    "current": index + 1,
                },
            )

            # 透传中间 chunk
            yield NodeOutput(
                data={"stream-audio": [{"audio_b64": audio_b64, "text": seg_text, "index": index}]},
                final=False,
            )
            index += 1

        total = len(collected)
        await emit.emit_node_update(
            context.node_id, "completed",
            f"播放完成 ({total} 段)",
            data={"mode": "stream", "segments": collected, "total": total},
        )

        yield NodeOutput(
            data={
                "stream-audio": collected,
                "batch-audio": None,
                "played": True,
                "mode": "stream",
                "segment_count": total,
            },
            final=True,
        )


# ── helpers ──

def _extract_b64_from_inputs(inputs: dict) -> str:
    """从 inputs 提取音频 base64，优先 stream 再 batch"""
    # 流式输入 (完整 segments 列表)
    segments = inputs.get("stream-audio", []) or []
    if isinstance(segments, list) and segments:
        return "".join(
            s.get("audio_b64", "") if isinstance(s, dict) else ""
            for s in segments
        )

    # 批量输入
    batch = inputs.get("batch-audio", None)
    if isinstance(batch, dict):
        return batch.get("audio_b64", "")
    if isinstance(batch, str):
        return batch
    return ""


def _audio_format(inputs: dict) -> str:
    batch = inputs.get("batch-audio", None)
    if isinstance(batch, dict):
        return batch.get("format", "wav")
    return "wav"
