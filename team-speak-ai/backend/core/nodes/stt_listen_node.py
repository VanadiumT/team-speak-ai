"""
STT 节点 — 语音转文本

从输入端口获取音频 → STT 转写 → 输出文本。
支持流式 (stream-in → stream-text-out) 和非流式 (batch-in → batch-text-out)。
"""

import logging

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry

logger = logging.getLogger(__name__)


@NodeRegistry.register("stt_listen")
class STTListenNode(BaseNode):
    """语音转文本节点"""

    node_type = "stt_listen"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
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
            await emit.emit_node_error(context.node_id, "未收到音频数据")
            return NodeOutput({"text": ""}, trigger_next=False)

        # 处理列表形式的音频分块 (来自 VAD 等)
        if isinstance(audio_data, list) and audio_data:
            import base64 as _b64
            pcm = bytearray()
            for chunk in audio_data:
                if isinstance(chunk, str):
                    try:
                        pcm.extend(_b64.b64decode(chunk))
                    except Exception:
                        pass
                elif isinstance(chunk, (bytes, bytearray)):
                    pcm.extend(chunk)
            audio_data = bytes(pcm)
        elif isinstance(audio_data, str):
            import base64 as _b64
            try:
                audio_data = _b64.b64decode(audio_data)
            except Exception:
                pass  # 不是 base64, 保持原样

        await emit.emit_node_update(
            context.node_id, "processing",
            "转写中...",
            data={"mode": "transcribing"},
        )

        try:
            text = await stt.transcribe(audio_data)
            text = text.strip() if text else ""
        except Exception as e:
            logger.exception(f"STT transcribe error")
            await emit.emit_node_error(context.node_id, str(e))
            return NodeOutput({"text": ""}, trigger_next=False)

        await emit.emit_node_update(
            context.node_id, "completed",
            f"转写完成 ({len(text)} 字)",
            data={"text": text},
        )

        return NodeOutput({"text": text})

    # ── STT 预设解析 ──

    @staticmethod
    def _resolve_stt_preset_config(cfg: dict) -> dict:
        from core.config.defaults import get_stt_preset_manager
        pm = get_stt_preset_manager()
        try:
            return pm.get_effective_config(
                cfg["platform_id"], cfg["model_id"],
                cfg.get("overrides"),
            )
        except (ValueError, KeyError) as e:
            logger.warning(f"STT preset not found ({e}), falling back to default")
            data = pm.list_all()
            platforms = data.get("platforms", [])
            for p in platforms:
                models = p.get("models", [])
                if not models:
                    continue
                default_model = next((m for m in models if m.get("is_default")), models[0])
                if default_model:
                    return pm.get_effective_config(p["id"], default_model["id"], cfg.get("overrides"))
            logger.warning("No STT presets available, falling back to legacy config")
            return STTListenNode._resolve_stt_legacy_config(cfg)

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
    def _get_stt_from_config(effective: dict):
        from core.stt.sensevoice_stt import SenseVoiceSTT
        from core.stt.whisper_stt import WhisperSTT
        from core.stt.minimax_stt import MiniMaxSTT

        provider = effective["provider"]
        if provider == "sensevoice":
            return SenseVoiceSTT(
                model_dir=effective.get("model_dir") or "iic/SenseVoiceSmall",
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
                api_url=effective.get("api_url", "https://api.minimax.chat/v1"),
            )
        raise ValueError(f"Unknown STT provider: {provider}")
