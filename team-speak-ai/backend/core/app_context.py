"""
AppContext —— 应用全局服务容器

所有服务的统一持有者，替代分散的 12+ 个 init_xxx()/get_xxx() 全局单例。
一次 create(), 全应用通过 get_app_context() 访问。
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from core.flow.manager import FlowManager
from core.history.manager import HistoryManager
from core.config.defaults import ConfigDefaultsManager
from core.config.presets.llm import PresetManager
from core.config.presets.tts import TtsPresetManager
from core.config.presets.stt import SttPresetManager
from core.config.presets.ocr import OcrPresetManager
from core.config.presets.vad import VadPresetManager
from core.config.presets.ts import TeamSpeakPresetManager
from core.variables.manager import SysVarManager
from core.upload.chunk_receiver import ChunkReceiver
from core.notification.manager import NotificationManager

if TYPE_CHECKING:
    from core.pipeline.engine import PipelineEngine

logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    """应用全局服务容器。

    所有服务实例集中管理，一次创建全应用共享。
    通过 get_app_context() 获取当前实例。
    """

    # ── 目录路径 ──
    data_dir: str = ""

    # ── 核心服务 ──
    flow_manager: Optional[FlowManager] = None
    history_manager: Optional[HistoryManager] = None
    defaults_manager: Optional[ConfigDefaultsManager] = None
    notification_manager: Optional[NotificationManager] = None
    sys_var_manager: Optional[SysVarManager] = None
    chunk_receiver: Optional[ChunkReceiver] = None
    pipeline_engine: Optional[PipelineEngine] = None

    # ── 预设管理器 ──
    preset_manager: Optional[PresetManager] = None              # LLM
    tts_preset_manager: Optional[TtsPresetManager] = None
    stt_preset_manager: Optional[SttPresetManager] = None
    ocr_preset_manager: Optional[OcrPresetManager] = None
    vad_preset_manager: Optional[VadPresetManager] = None
    ts_preset_manager: Optional[TeamSpeakPresetManager] = None

    # ── 后台任务 ──
    _cleanup_task: Optional[asyncio.Task] = field(default=None, repr=False)

    @classmethod
    def create(
        cls,
        data_dir: str,
        upload_dir: str,
        max_upload_size: int,
        pipeline_config_dir: str = "",
    ) -> "AppContext":
        """工厂方法：一次性创建所有服务。初始化顺序由此函数统一保证。"""
        ctx = cls(data_dir=data_dir)

        logger.info("Creating AppContext...")

        ctx.flow_manager = FlowManager(data_dir)
        logger.info("  FlowManager ready (%d flows)", len(ctx.flow_manager.list_flows()))

        ctx.history_manager = HistoryManager(data_dir)
        logger.info("  HistoryManager ready")

        ctx.defaults_manager = ConfigDefaultsManager(data_dir)
        logger.info("  ConfigDefaultsManager ready")

        ctx.preset_manager = PresetManager(data_dir)
        logger.info("  PresetManager (LLM) ready")

        ctx.tts_preset_manager = TtsPresetManager(data_dir)
        logger.info("  TtsPresetManager ready")

        ctx.stt_preset_manager = SttPresetManager(data_dir)
        logger.info("  SttPresetManager ready")

        ctx.ocr_preset_manager = OcrPresetManager(data_dir)
        logger.info("  OcrPresetManager ready")

        ctx.vad_preset_manager = VadPresetManager(data_dir)
        logger.info("  VadPresetManager ready")

        ctx.ts_preset_manager = TeamSpeakPresetManager(data_dir)
        logger.info("  TeamSpeakPresetManager ready")

        ctx.sys_var_manager = SysVarManager(data_dir)
        logger.info("  SysVarManager ready (%d variables)", len(ctx.sys_var_manager.list_all()))

        ctx.chunk_receiver = ChunkReceiver(upload_dir, max_upload_size)
        logger.info("  ChunkReceiver ready")

        ctx.notification_manager = NotificationManager(data_dir)
        logger.info("  NotificationManager ready")

        from core.pipeline.engine import engine as _module_engine  # 延迟导入避免循环依赖
        ctx.pipeline_engine = _module_engine  # 复用模块级单例，保证全局唯一
        logger.info("  PipelineEngine ready")

        logger.info("AppContext created successfully")
        return ctx

    async def shutdown(self):
        """统一生命周期清理。"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
        logger.info("AppContext shutdown complete")

    def start_background_tasks(self):
        """启动后台异步任务。"""
        self._cleanup_task = asyncio.create_task(
            self.chunk_receiver.cleanup_timeouts()
        )


# ── 唯一的一对全局存取函数 —— 整个项目只此一处 ──

_ctx: Optional[AppContext] = None


def set_app_context(ctx: AppContext) -> None:
    """设置全局 AppContext（由 main.py startup 调用一次）。"""
    global _ctx
    _ctx = ctx


def get_app_context() -> AppContext:
    """获取全局 AppContext。

    Raises:
        RuntimeError: 如果 AppContext 尚未初始化。
    """
    if _ctx is None:
        raise RuntimeError(
            "AppContext not initialized — call AppContext.create() and "
            "set_app_context() in startup_event first"
        )
    return _ctx
