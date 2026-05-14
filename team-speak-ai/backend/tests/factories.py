"""
测试数据工厂

提供便捷函数来构建测试所需的 flow JSON、node 定义、connection 等数据。
"""

import uuid
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.definition import (
    PipelineDefinition, NodeDefinition, ConnectionDef,
    InputMapping, TriggerConfig,
)


def make_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def make_node(
    node_id: str = None,
    node_type: str = "start",
    name: str = "",
    config: dict = None,
    position: dict = None,
    input_mappings: list = None,
    trigger: TriggerConfig = None,
    listener: bool = False,
) -> NodeDefinition:
    return NodeDefinition(
        id=node_id or make_id(node_type),
        type=node_type,
        name=name or node_type,
        position=position or {"x": 0, "y": 0},
        config=config or {},
        input_mappings=input_mappings or [],
        trigger=trigger,
        listener=listener,
    )


def make_connection(
    conn_id: str = None,
    from_node: str = "n1",
    from_port: str = "event-out",
    to_node: str = "n2",
    to_port: str = "trigger-in",
    conn_type: str = "event",
) -> ConnectionDef:
    return ConnectionDef(
        id=conn_id or make_id("conn"),
        from_node=from_node,
        from_port=from_port,
        to_node=to_node,
        to_port=to_port,
        type=conn_type,
    )


def make_flow(
    flow_id: str = "test_flow",
    name: str = "测试流程",
    nodes: list = None,
    connections: list = None,
    params: dict = None,
    group: str = "",
) -> PipelineDefinition:
    return PipelineDefinition(
        id=flow_id,
        name=name,
        group=group,
        nodes=nodes or [],
        connections=connections or [],
        params=params or {},
    )


def make_context(
    flow_id: str = "test_flow",
    execution_id: str = "exec_001",
    node_id: str = "node_01",
    node_type: str = "start",
    node_config: dict = None,
    inputs: dict = None,
    accumulated_context: dict = None,
) -> NodeContext:
    return NodeContext(
        flow_id=flow_id,
        execution_id=execution_id,
        node_id=node_id,
        node_type=node_type,
        node_config=node_config or {},
        inputs=inputs or {},
        accumulated_context=accumulated_context or {},
    )


def make_flow_json(
    flow_id: str = "test_flow",
    name: str = "测试流程",
    nodes: list = None,
    connections: list = None,
    params: dict = None,
) -> dict:
    """构建可直接写入 JSON 的 flow dict"""
    return {
        "id": flow_id,
        "name": name,
        "group": "",
        "icon": "account_tree",
        "enabled": True,
        "skill_prompt": "",
        "canvas": {"width": 2000, "height": 1500},
        "params": params or {},
        "nodes": nodes or [],
        "connections": connections or [],
    }


def make_node_json(
    node_id: str = "start_01",
    node_type: str = "start",
    name: str = "开始",
    config: dict = None,
) -> dict:
    return {
        "id": node_id,
        "type": node_type,
        "name": name,
        "position": {"x": 0, "y": 0},
        "config": config or {},
        "input_mappings": [],
        "trigger": None,
        "listener": False,
    }
