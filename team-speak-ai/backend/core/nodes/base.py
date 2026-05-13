"""
BaseNode — 所有节点的抽象基类
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional

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

    async def execute_stream(self, context: NodeContext, emit: EventEmitter) -> AsyncGenerator[NodeOutput, None]:
        """流式执行，逐块 yield NodeOutput(final=False)，最后 yield NodeOutput(final=True)。
        子类覆写此方法后，引擎会自动走流式路径。默认抛 NotImplementedError。"""
        raise NotImplementedError
