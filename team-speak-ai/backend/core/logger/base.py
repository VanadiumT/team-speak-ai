from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    timestamp: datetime
    level: LogLevel
    module_name: str
    message: str
    extra: dict = field(default_factory=dict)


@dataclass
class PipelineEvent:
    event_type: str
    pipeline_id: str
    execution_id: str
    node_id: Optional[str] = None
    data: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class BaseLogger(ABC):
    @abstractmethod
    def log(self, entry: LogEntry) -> None:
        """写入一条日志条目"""

    @abstractmethod
    def log_event(self, event: PipelineEvent) -> None:
        """写入一条结构化 Pipeline 事件"""

    @abstractmethod
    def close(self) -> None:
        """关闭 Logger，刷新并释放资源"""
