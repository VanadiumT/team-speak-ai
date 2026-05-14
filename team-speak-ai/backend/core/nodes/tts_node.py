"""
TTS 节点 — 文本转语音（流式/非流式）

配置通过 TTS 预设系统 (TtsPresetManager) 管理。
"""

import re
import base64
import logging
from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput, NodeState, _STREAM_END
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry
from core.tts.factory import TTSProvider, create_tts
from core.app_context import get_app_context
from config import settings

logger = logging.getLogger(__name__)


@NodeRegistry.register("tts")
class TTSNode(BaseNode):
    """语音合成节点"""

    node_type = "tts"

    def _split_sentences(self, text: str) -> list[str]:
        parts = re.split(r'(?<=[。！？.!?\n])', text)
        return [p.strip() for p in parts if p.strip()]

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        self.node_id = context.node_id
        cfg = context.node_config

        # ── 检测新旧配置格式 ──
        if cfg.get("platform_id") and cfg.get("model_id"):
            effective = self._resolve_preset_config(cfg)
        else:
            effective = self._resolve_legacy_config(cfg)

        # ── 获取输入文本 ──
        text = context.inputs.get("stream-text") or context.inputs.get("batch-text") or ""
        if not text or not text.strip():
            if not text:
                text = context.inputs.get("text") or context.inputs.get("response") or ""
        if not text or not text.strip():
            self._log_info("无文本可合成")
            await emit.emit_node_update(context.node_id, NodeState.COMPLETED, "无文本可合成")
            return NodeOutput({"stream-audio-out": "", "batch-audio-out": "", "segments": [], "text": ""})

        tts = self._build_tts(effective)
        sentences = self._split_sentences(text)
        model_name = effective.get("model", "")

        self._log_info(f"语音合成中 (0/{len(sentences)})")
        await emit.emit_node_update(
            context.node_id, "processing",
            f"语音合成中 (0/{len(sentences)})",
            data={"mode": "synthesizing", "total": len(sentences), "model": model_name},
        )

        if effective.get("streaming", True):
            return await self._execute_streaming(context, emit, tts, sentences, text, len(sentences), model_name)
        else:
            return await self._execute_batch(context, emit, tts, sentences, text, len(sentences), model_name)

    async def execute_stream(self, context: NodeContext, emit: EventEmitter):
        """逐块接收 LLM 文本（从 context._stream_input），缓冲到句子边界后合成语音，逐段 yield"""
        cfg = context.node_config

        if cfg.get("platform_id") and cfg.get("model_id"):
            effective = self._resolve_preset_config(cfg)
        else:
            effective = self._resolve_legacy_config(cfg)

        tts = self._build_tts(effective)
        chunk_queue = context.stream_input
        model_name = effective.get("model", "")
        SENTENCE_RE = re.compile(r'[。！？.!?\n]')

        buffer = ""
        all_audio = b""
        segments = []
        seg_idx = 0

        await emit.emit_node_update(
            context.node_id, "processing",
            f"语音合成中 (0)",
            data={"mode": "synthesizing", "total": 0, "model": model_name},
        )

        try:
            while True:
                chunk = await chunk_queue.get()
                if chunk is _STREAM_END:
                    if buffer.strip():
                        audio_bytes = await tts.synthesize(buffer.strip())
                        all_audio += audio_bytes
                        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
                        segments.append({"text": buffer.strip(), "audio_b64": audio_b64, "index": seg_idx})
                        await emit.emit_node_update(
                            context.node_id, "processing",
                            f"语音合成中 ({seg_idx + 1})",
                            data={"segment_index": seg_idx, "segment_text": buffer.strip(),
                                  "audio_b64": audio_b64},
                        )
                        yield NodeOutput({"segment_index": seg_idx, "segment_text": buffer.strip(),
                                          "audio_b64": audio_b64, "progress": 1.0}, final=False)
                        seg_idx += 1
                    break

                if chunk.data.get("content_chunk"):
                    buffer += chunk.data["content_chunk"]

                # 提取完整句子
                while True:
                    m = SENTENCE_RE.search(buffer)
                    if not m:
                        break
                    sentence = buffer[:m.end()].strip()
                    buffer = buffer[m.end():]
                    if sentence:
                        audio_bytes = await tts.synthesize(sentence)
                        all_audio += audio_bytes
                        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
                        segments.append({"text": sentence, "audio_b64": audio_b64, "index": seg_idx})
                        await emit.emit_node_update(
                            context.node_id, "processing",
                            f"语音合成中 ({seg_idx + 1})",
                            progress=(seg_idx + 1) / max(seg_idx + 2, 1),
                            data={"segment_index": seg_idx, "segment_text": sentence,
                                  "audio_b64": audio_b64},
                        )
                        yield NodeOutput({"segment_index": seg_idx, "segment_text": sentence,
                                          "audio_b64": audio_b64}, final=False)
                        seg_idx += 1

        except Exception as e:
            self._log_exception("TTS streaming error")
            raise self._wrap_error("TTS streaming error", e) from e

        # 最终输出
        full_audio_b64 = base64.b64encode(all_audio).decode("ascii") if all_audio else ""
        total = seg_idx
        await emit.emit_node_complete(
            context.node_id,
            {"audio_b64": full_audio_b64, "segments": segments, "model": model_name},
        )
        yield NodeOutput({
            "stream-audio-out": full_audio_b64,
            "batch-audio-out": full_audio_b64,
            "segments": segments,
            "text": "".join(s["text"] for s in segments),
            "total_segments": total,
        }, final=True)

    # ═══════════════════════════════════════════════════════

    @staticmethod
    def _resolve_preset_config(cfg: dict) -> dict:
        pm = get_app_context().tts_preset_manager
        return BaseNode._resolve_preset_with_fallback(cfg, pm, legacy_fn=TTSNode._resolve_legacy_config)

    @staticmethod
    def _resolve_legacy_config(cfg: dict) -> dict:
        engine = cfg.get("engine", settings.tts_provider)
        if engine == "edge":
            default_voice = cfg.get("voice") or settings.edge_tts_voice
        else:
            default_voice = cfg.get("voice") or settings.minimax_voice_id
        return {
            "provider": engine,
            "api_key": settings.minimax_api_key,
            "model": settings.minimax_tts_model,
            "voice_id": default_voice,
            "speed": cfg.get("speed", settings.minimax_speed),
            "vol": cfg.get("vol", settings.minimax_vol),
            "pitch": 0,
            "emotion": "",
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1,
            "streaming": False,
            "language_boost": None,
        }

    @staticmethod
    def _build_tts(effective: dict):
        provider = TTSProvider(effective["provider"])
        if provider == TTSProvider.EDGE:
            tts_config = {
                "voice": effective.get("voice_id") or settings.edge_tts_voice,
            }
        else:
            tts_config = {
                "api_key": effective.get("api_key", ""),
                "model": effective.get("model", "speech-2.8-hd"),
                "voice_id": effective.get("voice_id", "male-qn-qingse"),
                "speed": effective.get("speed", 1.0),
                "vol": effective.get("vol", 1.0),
                "pitch": effective.get("pitch", 0),
                "emotion": effective.get("emotion") or "",
                "sample_rate": effective.get("sample_rate", 32000),
                "bitrate": effective.get("bitrate", 128000),
                "file_format": effective.get("format", "mp3"),
                "channel": effective.get("channel", 1),
                "language_boost": effective.get("language_boost"),
            }
        return create_tts(provider, tts_config)

    # ═══════════════════════════════════════════════════════
    # Execute modes
    # ═══════════════════════════════════════════════════════

    async def _synthesize_all(self, context, emit, tts, sentences, text, total,
                               model_name="", rich_progress=False):
        """统一的合成循环：逐句合成 → base64 → 进度通知 → 返回 NodeOutput"""
        segments = []
        all_audio = b""
        for i, sentence in enumerate(sentences):
            audio_bytes = await tts.synthesize(sentence)
            all_audio += audio_bytes
            audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
            segments.append({"text": sentence, "audio_b64": audio_b64, "index": i})
            if rich_progress:
                await emit.emit_node_update(context.node_id, NodeState.PROCESSING,
                    f"语音合成中 ({i+1}/{total})",
                    data={"segment_index": i, "segment_text": sentence,
                          "audio_b64": audio_b64, "progress": (i+1)/total if total else 1})
            else:
                await emit.emit_node_update(context.node_id, NodeState.PROCESSING,
                    f"语音合成中 ({i+1}/{total})",
                    progress=(i+1)/total if total else 1)
        full_audio_b64 = base64.b64encode(all_audio).decode("ascii")
        await emit.emit_node_update(context.node_id, NodeState.COMPLETED,
            f"合成完成 ({total} 句)",
            data={"audio_b64": full_audio_b64, "segments": segments, "model": model_name})
        return NodeOutput({
            "stream-audio-out": full_audio_b64, "batch-audio-out": full_audio_b64,
            "segments": segments, "text": text, "total_segments": total,
        })

    async def _execute_streaming(self, context, emit, tts, sentences, text, total, model_name=""):
        return await self._synthesize_all(context, emit, tts, sentences, text, total, model_name, rich_progress=True)

    async def _execute_batch(self, context, emit, tts, sentences, text, total, model_name=""):
        return await self._synthesize_all(context, emit, tts, sentences, text, total, model_name, rich_progress=False)
