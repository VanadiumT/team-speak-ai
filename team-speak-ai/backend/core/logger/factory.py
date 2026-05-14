import os
from enum import Enum
from core.logger.base import BaseLogger, LogLevel
from core.logger.file_logger import FileLogger


class LoggerProvider(Enum):
    FILE = "file"


def create_logger(provider: LoggerProvider, config: dict) -> BaseLogger:
    if provider == LoggerProvider.FILE:
        log_dir = config.get("log_dir", "logs")
        # 相对路径锚定到 backend 目录
        if not os.path.isabs(log_dir):
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            log_dir = os.path.join(backend_dir, log_dir)
        return FileLogger(
            log_dir=log_dir,
            keep_days=config.get("keep_days", 30),
            min_level=config.get("min_level", LogLevel.DEBUG),
        )
    raise ValueError(f"Unknown logger provider: {provider}")
