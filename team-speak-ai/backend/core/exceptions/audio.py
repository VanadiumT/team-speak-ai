"""音频处理相关异常"""
from __future__ import annotations

from typing import Optional

from core.exceptions.base import AppBaseException


class AudioBusError(AppBaseException):
    """音频总线错误（订阅/发布失败等）"""

    error_code = "AUDIO_BUS_ERROR"

    def __init__(self, detail: str, cause: Optional[Exception] = None):
        super().__init__(message=f"AudioBus error: {detail}", cause=cause)


class AudioDecodeError(AppBaseException):
    """音频解码错误（格式不支持、数据损坏等）"""

    error_code = "AUDIO_DECODE_ERROR"

    def __init__(self, detail: str, cause: Optional[Exception] = None):
        super().__init__(message=f"Audio decode error: {detail}", cause=cause)
