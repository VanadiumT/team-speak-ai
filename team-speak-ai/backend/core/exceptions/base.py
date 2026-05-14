"""异常基类 — 所有自定义异常的根"""
from __future__ import annotations

from typing import Any, Optional


class AppBaseException(Exception):
    """应用级异常基类，携带结构化上下文"""

    error_code: str = "APP_ERROR"

    def __init__(
        self,
        message: str = "",
        context: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.cause = cause

    def to_dict(self) -> dict[str, Any]:
        """返回结构化错误信息，用于 WS 响应和日志"""
        from core.logger.context import get_trace_id

        result: dict[str, Any] = {
            "error_code": self.error_code,
            "message": self.message,
        }
        if self.context:
            result["context"] = self.context
        trace_id = get_trace_id()
        if trace_id:
            result["trace_id"] = trace_id
        if self.cause:
            result["cause"] = str(self.cause)
        return result
