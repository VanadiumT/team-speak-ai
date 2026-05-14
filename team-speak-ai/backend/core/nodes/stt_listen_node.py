"""
STT 节点 — 语音转文本

从输入端口获取音频 → STT 转写 → 输出文本。
支持流式 (stream-in → stream-text-out) 和非流式 (batch-in → batch-text-out)。
"""

import logging

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput, NodeState
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry

logger = logging.getLogger(__name__)


@NodeRegistry.register("stt_listen")
class STTListenNode(BaseNode):
    """语音转文本节点"""

    node_type = "stt_listen"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        self.node_id = context.node_id
        cfg = context.node_config

        # 预设解析
        if cfg.get("platform_id") and cfg.get("model_id"):
            effective = self._resolve_stt_preset_config(cfg)
        else:
            effective = self._resolve_stt_legacy_config(cfg)
        stt = self._get_stt_from_config(effective)

        # 获取音频数据：流式优先，否则非流式，也兼容 stt-stream
        audio_data = context.inputs.get("stream-audio") or context.inputs.get("batch-audio") or context.inputs.get("stt-stream")
        if not audio_data:
            self._log_warning("未收到音频数据")
            await emit.emit_node_error(context.node_id, "未收到音频数据")
            return NodeOutput({"text": ""}, trigger_next=False)

        audio_data = self._decode_audio_input(audio_data)

        self._log_info("转写中...")
        await emit.emit_node_update(
            context.node_id, NodeState.PROCESSING,
            "转写中...",
            data={"mode": "transcribing"},
        )

        try:
            text = await stt.transcribe(audio_data)
            text = text.strip() if text else ""
        except Exception as e:
            self._log_exception("STT transcribe error")
            raise self._wrap_error("STT transcribe error", e) from e

        self._log_info(f"转写完成 ({len(text)} 字)")
        await emit.emit_node_update(
            context.node_id, "completed",
            f"转写完成 ({len(text)} 字)",
            data={"text": text},
        )

        return NodeOutput({"text": text})

    # ── STT 预设解析 ──

    @staticmethod
    def _resolve_stt_preset_config(cfg: dict) -> dict:
        from core.app_context import get_app_context
        pm = get_app_context().stt_preset_manager
        return BaseNode._resolve_preset_with_fallback(cfg, pm, legacy_fn=STTListenNode._resolve_stt_legacy_config)

    @staticmethod
    def _resolve_stt_legacy_config(cfg: dict) -> dict:
        from config import settings
        provider = cfg.get("engine", settings.stt_provider)
        return {
            "provider": provider,
            "api_key": settings.minimax_api_key,
            "api_url": settings.minimax_api_url,
            "model_dir": settings.sensevoice_model,
            "device": settings.sensevoice_device if provider == "sensevoice" else (
                settings.whisper_device if provider == "whisper" else "cpu"
            ),
            "model_name": settings.whisper_model if provider == "whisper" else "default",
            "language": "auto",
            "sample_rate": cfg.get("sample_rate", 16000),
        }

    @staticmethod
    def _decode_audio_input(audio_data) -> bytes:
        """将上游输入统一解码为 raw PCM bytes"""
        import base64 as _b64
        if isinstance(audio_data, list):
            pcm = bytearray()
            for chunk in audio_data:
                pcm.extend(_b64.b64decode(chunk) if isinstance(chunk, str) else chunk)
            return bytes(pcm)
        if isinstance(audio_data, str):
            return _b64.b64decode(audio_data)
        if isinstance(audio_data, (bytes, bytearray)):
            return bytes(audio_data)
        raise TypeError(f"Unsupported audio input type: {type(audio_data)}")

    @staticmethod
    def _get_stt_from_config(effective: dict):
        from core.stt.sensevoice_stt import SenseVoiceSTT
        from core.stt.whisper_stt import WhisperSTT
        from core.stt.minimax_stt import MiniMaxSTT
        from core.exceptions import ProviderConnectionError

        provider = effective["provider"]
        if provider == "sensevoice":
            return SenseVoiceSTT(
                model_dir=effective.get("model_dir") or settings.sensevoice_model,
                device=effective.get("device", "cpu"),
            )
        elif provider == "whisper":
            return WhisperSTT(
                model_name=effective.get("model_name", "base"),
                device=effective.get("device", "cuda"),
            )
        elif provider == "minimax":
            return MiniMaxSTT(
                api_key=effective["api_key"] or "",
                api_url=effective.get("api_url") or settings.minimax_api_url,
            )
        raise ProviderConnectionError(provider=provider, detail=f"Unknown STT provider: {provider}")
