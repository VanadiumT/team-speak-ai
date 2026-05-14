"""trace_id 上下文管理 — 通过 contextvars 实现 async 安全的请求链路追踪"""
from __future__ import annotations

import contextvars
import uuid
from contextlib import contextmanager
from typing import Generator

trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")


def get_trace_id() -> str:
    """获取当前上下文的 trace_id"""
    return trace_id_var.get()


def set_trace_id(trace_id: str) -> contextvars.Token[str]:
    """设置 trace_id，返回 Token 用于回滚"""
    return trace_id_var.set(trace_id)


def generate_trace_id() -> str:
    """生成新的 trace_id（短格式，8 位 hex）"""
    return uuid.uuid4().hex[:8]


@contextmanager
def trace_context(trace_id: str | None = None) -> Generator[str, None, None]:
    """上下文管理器：自动设置和恢复 trace_id

    用法:
        with trace_context() as tid:
            # 此作用域内所有日志自动携带 tid
            logger.info("processing...")

        with trace_context("custom-id"):
            # 使用指定的 trace_id
            ...
    """
    tid = trace_id or generate_trace_id()
    token = set_trace_id(tid)
    try:
        yield tid
    finally:
        trace_id_var.reset(token)
