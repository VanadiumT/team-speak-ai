"""
节点执行上下文和状态
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class NodeState(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    LISTENING = "listening"  # 常驻监听节点等待音频输入


@dataclass
class NodeOutput:
    """节点执行输出"""
    data: dict = field(default_factory=dict)
    trigger_next: bool = True  # 是否自动触发下游


@dataclass
class NodeContext:
    """节点执行上下文"""
    pipeline_id: str
    execution_id: str
    node_id: str
    node_type: str
    node_config: dict
    inputs: dict                    # 来自上游的输入数据
    state: NodeState = NodeState.PENDING
    accumulated_context: dict = field(default_factory=dict)  # 整个 pipeline 的累积上下文


@dataclass
class NodeRuntime:
    """节点运行时状态"""
    node_def_id: str
    status: NodeState = NodeState.PENDING
    output: Optional[NodeOutput] = None
    error: Optional[str] = None
    summary: str = ""
    progress: Optional[float] = None
    data: dict = field(default_factory=dict)
