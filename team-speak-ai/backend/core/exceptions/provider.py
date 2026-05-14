"""AI Provider 调用相关异常"""
from __future__ import annotations

from typing import Any, Optional

from core.exceptions.base import AppBaseException


class ProviderConnectionError(AppBaseException):
    """Provider 连接失败（网络不可达、DNS 解析失败等）"""

    error_code = "PROVIDER_CONNECTION"

    def __init__(self, provider: str, detail: str, cause: Optional[Exception] = None):
        super().__init__(
            message=f"Provider [{provider}] connection failed: {detail}",
            context={"provider": provider},
            cause=cause,
        )
        self.provider = provider


class ProviderTimeoutError(AppBaseException):
    """Provider 调用超时"""

    error_code = "PROVIDER_TIMEOUT"

    def __init__(self, provider: str, detail: str = "Request timed out", cause: Optional[Exception] = None):
        super().__init__(
            message=f"Provider [{provider}] timed out: {detail}",
            context={"provider": provider},
            cause=cause,
        )
        self.provider = provider


class ProviderAuthError(AppBaseException):
    """Provider 认证失败（API key 无效、权限不足等）"""

    error_code = "PROVIDER_AUTH"

    def __init__(self, provider: str, detail: str = "Authentication failed", cause: Optional[Exception] = None):
        super().__init__(
            message=f"Provider [{provider}] auth error: {detail}",
            context={"provider": provider},
            cause=cause,
        )
        self.provider = provider
