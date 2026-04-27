from enum import Enum
from core.logger.base import BaseLogger
from core.logger.file_logger import FileLogger


class LoggerProvider(Enum):
    FILE = "file"


def create_logger(provider: LoggerProvider, config: dict) -> BaseLogger:
    if provider == LoggerProvider.FILE:
        return FileLogger(
            log_dir=config.get("log_dir", "logs"),
            keep_days=config.get("keep_days", 30),
        )
    raise ValueError(f"Unknown logger provider: {provider}")
