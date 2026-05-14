"""
BaseNode — 所有节点的抽象基类
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Optional

from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter

logger = logging.getLogger(__name__)


class BaseNode(ABC):
    """节点基类，所有节点继承此类"""

    node_type: str = ""

    def __init__(self, config: dict):
        self.config = config
        self.node_id: str = ""  # 由引擎在执行前设置

    # ── 统一日志模板 ──

    def _log(self, level: str, msg: str, **kw: Any) -> None:
        """统一格式: [{NodeType}:{NodeId}] {msg}"""
        tag = f"[{self.__class__.__name__}:{self.node_id}]" if self.node_id else f"[{self.__class__.__name__}]"
        getattr(logger, level)(f"{tag} {msg}", **kw)

    def _log_debug(self, msg: str, **kw: Any) -> None:
        self._log("debug", msg, **kw)

    def _log_info(self, msg: str, **kw: Any) -> None:
        self._log("info", msg, **kw)

    def _log_warning(self, msg: str, **kw: Any) -> None:
        self._log("warning", msg, **kw)

    def _log_error(self, msg: str, **kw: Any) -> None:
        self._log("error", msg, **kw)

    def _log_exception(self, msg: str) -> None:
        """记录异常日志（含堆栈）"""
        tag = f"[{self.__class__.__name__}:{self.node_id}]" if self.node_id else f"[{self.__class__.__name__}]"
        logger.exception(f"{tag} {msg}")

    def _wrap_error(self, detail: str, cause: Optional[Exception] = None) -> "NodeExecutionError":
        """将当前节点的错误包装为 NodeExecutionError，由引擎层统一捕获"""
        from core.exceptions import NodeExecutionError
        return NodeExecutionError(
            node_id=self.node_id,
            node_type=self.__class__.__name__,
            detail=detail,
            cause=cause,
        )

    @staticmethod
    def _resolve_preset_with_fallback(cfg: dict, pm, legacy_fn=None, fallback_default=None):
        """统一的预设解析：get_effective_config → 默认 preset 回退 → legacy 兜底

        Args:
            cfg: 节点配置 dict，需含 platform_id / model_id
            pm:  preset manager 实例
            legacy_fn: 无 preset 时的兜底函数 (cfg) -> dict
            fallback_default: 无 preset 且无 legacy_fn 时返回的硬编码默认值
        """
        try:
            return pm.get_effective_config(cfg["platform_id"], cfg["model_id"], cfg.get("overrides"))
        except (ValueError, KeyError) as e:
            logger.warning(f"Preset not found ({e}), falling back to default")
            data = pm.list_all()
            for p in data.get("platforms", []):
                models = p.get("models", [])
                if not models:
                    continue
                default = next((m for m in models if m.get("is_default")), models[0])
                if default:
                    return pm.get_effective_config(p["id"], default["id"], cfg.get("overrides"))
            if legacy_fn:
                logger.warning("No presets available, falling back to legacy config")
                return legacy_fn(cfg)
            if fallback_default is not None:
                logger.warning("No presets available, using hardcoded defaults")
                return fallback_default
            raise ValueError(f"No presets available and no fallback configured")

    @abstractmethod
    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        """
        执行节点逻辑

        Args:
            context: 节点执行上下文，包含 inputs 和 accumulated_context
            emit: 事件发射器，用于实时推送到前端

        Returns:
            NodeOutput: 输出数据
        """
        ...

    async def execute_stream(self, context: NodeContext, emit: EventEmitter) -> AsyncGenerator[NodeOutput, None]:
        """流式执行，逐块 yield NodeOutput(final=False)，最后 yield NodeOutput(final=True)。
        子类覆写此方法后，引擎会自动走流式路径。默认抛 NotImplementedError。"""
        raise NotImplementedError
