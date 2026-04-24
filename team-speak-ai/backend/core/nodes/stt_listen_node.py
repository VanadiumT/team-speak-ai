"""
STT Listen 节点 — 常驻后台监听 TeamSpeak 语音

从 AudioBus 获取 TS 音频 → STT 转写 → 检测关键词 → 触发下游

核心逻辑：
- 订阅 AudioBus 获取实时音频
- 每段音频积累到 AudioBuffer，检测到语音结束后进行 STT
- 将 STT 结果推送前端（实时展示）
- 检测是否含有关键词，检测到则返回（触发下游 LLM 链）
- 未检测到则继续监听
"""

import asyncio
import base64
import logging

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry
from core.audio.audio_buffer import AudioBuffer
from core.audio.audio_bus import audio_bus
from core.stt.factory import STTProvider, create_stt
from config import settings

logger = logging.getLogger(__name__)


@NodeRegistry.register("stt_listen")
class STTListenNode(BaseNode):
    """TS 语音持续监听节点（常驻后台）"""

    node_type = "stt_listen"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        keywords = context.node_config.get("keywords", [])
        listener_id = f"stt_listen_{context.execution_id}"
        stt = self._get_stt()

        buffer = AudioBuffer(timeout=2.0)
        audio_bus.subscribe(listener_id)
        accumulated_text = ""

        try:
            await emit.emit_node_update(
                context.node_id,
                "processing",
                f"监听中 (关键词: {', '.join(keywords) or '无'})",
                data={"mode": "listening", "keywords": keywords},
            )

            while True:
                # 从 AudioBus 获取音频数据（非阻塞）
                frame = await audio_bus.get_audio(listener_id, timeout=0.5)
                if frame is None:
                    # 检查前一次累积的 buffer 是否超时
                    # 但这里我们不需要清理，除非特别大
                    continue

                audio_bytes = frame.get("data", b"")
                sender_id = frame.get("sender_id", 0)

                if not audio_bytes:
                    continue

                # 添加到 AudioBuffer
                # 使用 sender_id=0 因为 TS 监听不分说话者
                import time
                seq = int(time.time() * 1000)
                buffer.add_frame(0, audio_bytes, seq, seq)

                # 检测是否完成（超时 2s 或小帧）
                if len(audio_bytes) < 5000 or buffer.is_complete(0):
                    full_audio = buffer.get_audio(0)
                    if full_audio and len(full_audio) > 1000:
                        try:
                            text = await stt.transcribe(full_audio)
                            buffer.clear(0)
                        except Exception as e:
                            logger.error(f"STT error: {e}")
                            buffer.clear(0)
                            continue

                        if text and text.strip():
                            accumulated_text += text + "\n"

                            # 推送实时转写结果到前端
                            await emit.emit_node_update(
                                context.node_id,
                                "processing",
                                f"识别: {text[:40]}{'...' if len(text) > 40 else ''}",
                                data={
                                    "partial_text": text,
                                    "accumulated": accumulated_text,
                                    "mode": "listening",
                                },
                            )

                            logger.info(f"STTListen [{context.execution_id}]: {text[:60]}")

                            # 关键词检测
                            if keywords:
                                for kw in keywords:
                                    if kw in accumulated_text or kw in text:
                                        logger.info(f"Keyword detected: '{kw}' in STT text")
                                        await emit.emit_node_update(
                                            context.node_id,
                                            "completed",
                                            f"关键词 '{kw}' 触发!",
                                            data={
                                                "trigger_keyword": kw,
                                                "text": accumulated_text.strip(),
                                            },
                                        )
                                        await emit.emit_important_update(
                                            "关键词触发",
                                            f"检测到关键词 '{kw}'，启动 AI 流程",
                                            "status",
                                        )
                                        return NodeOutput({
                                            "text": accumulated_text.strip(),
                                            "stt_raw": text,
                                            "trigger_keyword": kw,
                                        })

        except asyncio.CancelledError:
            logger.info(f"STTListen cancelled: {context.execution_id}")
            raise
        finally:
            audio_bus.unsubscribe(listener_id)
            buffer.clear(0)

        # 理论上不会到达这里（循环仅在返回或异常时退出）
        return NodeOutput({"text": accumulated_text.strip()})

    @staticmethod
    def _get_stt():
        """获取 STT 实例（复用已有工厂方法）"""
        provider = STTProvider(settings.stt_provider)
        stt_config = {
            "whisper": {
                "model_name": settings.whisper_model,
                "device": settings.whisper_device,
            },
            "minimax": {
                "api_key": settings.minimax_api_key,
                "api_url": settings.minimax_api_url,
            },
            "sensevoice": {
                "model_dir": settings.sensevoice_model,
                "device": settings.sensevoice_device,
            },
        }
        config = stt_config.get(settings.stt_provider, stt_config["whisper"])
        return create_stt(provider, config)
