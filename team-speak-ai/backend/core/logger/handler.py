import logging
import sys
from datetime import datetime
from typing import Optional

from core.logger.base import BaseLogger, LogEntry, LogLevel, PipelineEvent
from core.logger.context import get_trace_id

_logger: Optional[BaseLogger] = None


class TraceIdFilter(logging.Filter):
    """将 trace_id 注入 LogRecord，供 console 格式串使用"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id()  # type: ignore[attr-defined]
        return True


class LoggingHandler(logging.Handler):
    """将标准 logging.LogRecord 转发到 BaseLogger，自动注入 trace_id"""

    def __init__(self, level: int = logging.NOTSET):
        super().__init__(level)

    def emit(self, record: logging.LogRecord) -> None:
        if _logger is None:
            return
        try:
            entry = LogEntry(
                timestamp=datetime.fromtimestamp(record.created),
                level=LogLevel[record.levelname],
                module_name=record.name,
                message=record.getMessage(),
                extra={"trace_id": get_trace_id()},
            )
            _logger.log(entry)
        except Exception:
            self.handleError(record)


def install_logger(logger_instance: BaseLogger) -> None:
    """安装全局 Logger，同时将 LoggingHandler 注册到 root logger"""
    global _logger
    _logger = logger_instance

    root = logging.getLogger()
    handler = LoggingHandler()
    root.addHandler(handler)


def log_pipeline_event(event: PipelineEvent) -> None:
    """转发结构化 Pipeline 事件到全局 Logger"""
    global _logger
    if _logger is not None:
        try:
            _logger.log_event(event)
        except Exception:
            pass


def close_logger() -> None:
    """关闭全局 Logger"""
    global _logger
    if _logger is not None:
        try:
            _logger.close()
        except Exception:
            pass
        _logger = None
