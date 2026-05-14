"""流程管理相关异常"""
from __future__ import annotations

from core.exceptions.base import AppBaseException


class FlowNotFoundError(AppBaseException):
    """流程文件不存在"""

    error_code = "FLOW_NOT_FOUND"

    def __init__(self, flow_id: str):
        super().__init__(
            message=f"Flow not found: {flow_id}",
            context={"flow_id": flow_id},
        )
        self.flow_id = flow_id


class FlowValidationError(AppBaseException):
    """流程校验失败（端口不匹配、缺少必要节点等）"""

    error_code = "FLOW_VALIDATION"

    def __init__(self, flow_id: str, detail: str):
        super().__init__(
            message=f"Flow [{flow_id}] validation failed: {detail}",
            context={"flow_id": flow_id},
        )
        self.flow_id = flow_id


class FlowCycleError(AppBaseException):
    """流程 DAG 存在循环"""

    error_code = "FLOW_CYCLE"

    def __init__(self, flow_id: str, cycle_path: str = ""):
        msg = f"Flow [{flow_id}] has a cycle"
        if cycle_path:
            msg += f": {cycle_path}"
        super().__init__(
            message=msg,
            context={"flow_id": flow_id, "cycle_path": cycle_path},
        )
        self.flow_id = flow_id
