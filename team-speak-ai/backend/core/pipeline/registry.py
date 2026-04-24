"""
节点类型注册表
"""

from typing import Type


class NodeRegistry:
    """节点注册表：type → NodeClass 映射"""

    _registry: dict[str, Type] = {}

    @classmethod
    def register(cls, node_type: str):
        """装饰器，注册节点类"""
        def decorator(node_cls):
            cls._registry[node_type] = node_cls
            return node_cls
        return decorator

    @classmethod
    def create(cls, node_type: str, config: dict) -> Type:
        """创建节点实例"""
        node_cls = cls._registry.get(node_type)
        if not node_cls:
            raise ValueError(f"Unknown node type: {node_type}")
        return node_cls(config)

    @classmethod
    def list_types(cls) -> list[str]:
        return list(cls._registry.keys())
