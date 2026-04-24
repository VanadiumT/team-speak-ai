"""
BaseNode — 所有节点的抽象基类
"""

from abc import ABC, abstractmethod
from typing import Optional

from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter


class BaseNode(ABC):
    """节点基类，所有节点继承此类"""

    node_type: str = ""

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        """
        执行节点逻辑

        Args:
            context: 节点执行上下文，包含 inputs 和 accumulated_context
            emit: 事件发射器，用于实时推送到前端

        Returns:
            NodeOutput: 输出数据
        """
        ...
