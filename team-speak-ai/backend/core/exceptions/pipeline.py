"""流程引擎 / 节点执行相关异常"""
from __future__ import annotations

from typing import Any, Optional

from core.exceptions.base import AppBaseException


class PipelineError(AppBaseException):
    """流程级错误（加载、启动、停止等）"""

    error_code = "PIPELINE_ERROR"

    def __init__(self, flow_id: str, message: str, **kwargs: Any):
        super().__init__(message, context={"flow_id": flow_id}, **kwargs)
        self.flow_id = flow_id


class NodeExecutionError(AppBaseException):
    """节点执行错误 — 引擎层统一捕获"""

    error_code = "NODE_EXECUTION"

    def __init__(
        self,
        node_id: str,
        node_type: str,
        detail: str,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=f"[{node_type}:{node_id}] {detail}",
            context={"node_id": node_id, "node_type": node_type},
            cause=cause,
        )
        self.node_id = node_id
        self.node_type = node_type


class NodeConfigError(AppBaseException):
    """节点配置错误（缺少必填参数、类型不匹配等）"""

    error_code = "NODE_CONFIG"

    def __init__(self, node_id: str, node_type: str, detail: str):
        super().__init__(
            message=f"[{node_type}:{node_id}] Config error: {detail}",
            context={"node_id": node_id, "node_type": node_type},
        )
        self.node_id = node_id
        self.node_type = node_type


class StreamingError(AppBaseException):
    """流式处理错误（chunk 读取/写入失败等）"""

    error_code = "STREAMING_ERROR"

    def __init__(self, node_id: str, detail: str, cause: Optional[Exception] = None):
        super().__init__(
            message=f"[stream:{node_id}] {detail}",
            context={"node_id": node_id},
            cause=cause,
        )
        self.node_id = node_id
