"""
节点/连线编辑命令处理器

处理 node.*、connection.*、port.*、undo/redo、config.* 系列命令。
从 ws_main.py 拆分，共享工具函数通过 import 引用。
"""

import uuid
import logging

from fastapi import WebSocket

from core.app_context import get_app_context
from core.pipeline.definition import (
    NodeDefinition, ConnectionDef, TriggerConfig, InputMapping,
    port_input_key, port_output_key,
)
from api.routes.ws_utils import _send, _send_ack, _send_error

logger = logging.getLogger(__name__)


def _get_broadcast_to_flow():
    from api.routes.ws_main import _broadcast_to_flow
    return _broadcast_to_flow

def _get_push_history_state():
    from api.routes.ws_main import _push_history_state
    return _push_history_state


# ── 节点 CRUD ──────────────────────────────────────────────────

async def handle_node_create(websocket: WebSocket, flow_id: str, msg_id: str,
                             params: dict) -> None:
    fm = get_app_context().flow_manager
    node_type = params["node_type"]
    position = params.get("position", {"x": 0, "y": 0})

    from core.pipeline.registry import NodeRegistry
    type_def = NodeRegistry.get_type_def(node_type)

    node_id = f"{node_type}_{uuid.uuid4().hex[:6]}"
    node = NodeDefinition(
        id=node_id,
        type=node_type,
        name=params.get("name") or type_def.name,
        position=position,
        config=dict(params.get("config") or type_def.default_config),
    )
    await fm.add_node(flow_id, node)

    try:
        hm = get_app_context().history_manager
        await hm.record_operation(flow_id, "node.create",
                            forward={"node_id": node_id, "node_type": node_type, "position": position},
                            reverse={"node_id": node_id})
    except RuntimeError as e:
        logger.debug(f"History manager unavailable: {e}")

    await _send_ack(websocket, flow_id, msg_id)
    node_data = fm._serialize_flow(fm.load_flow(flow_id))["nodes"][-1]
    await _get_broadcast_to_flow()(flow_id, "node.created", {"node": node_data})
    await _get_push_history_state()(websocket, flow_id)


async def handle_node_delete(websocket: WebSocket, flow_id: str, msg_id: str,
                             params: dict) -> None:
    fm = get_app_context().flow_manager
    node_id = params["node_id"]

    flow = fm.load_flow(flow_id)
    node = flow.get_node(node_id)
    if not node:
        raise ValueError(f"Node not found: {node_id}")
    saved = fm._serialize_flow(flow)["nodes"]
    saved_node = next((n for n in saved if n["id"] == node_id), None)

    await fm.remove_node(flow_id, node_id)

    try:
        hm = get_app_context().history_manager
        await hm.record_operation(flow_id, "node.delete",
                            forward={"node_id": node_id},
                            reverse={"node": saved_node})
    except RuntimeError as e:
        logger.debug(f"History manager unavailable: {e}")

    await _send_ack(websocket, flow_id, msg_id)
    await _get_broadcast_to_flow()(flow_id, "node.deleted", {"node_id": node_id})
    await _get_push_history_state()(websocket, flow_id)


async def handle_node_move(websocket: WebSocket, flow_id: str, msg_id: str,
                           params: dict) -> None:
    fm = get_app_context().flow_manager
    node_id = params["node_id"]
    pos = params["position"]

    flow = fm.load_flow(flow_id)
    node = flow.get_node(node_id)
    if not node:
        raise ValueError(f"Node not found: {node_id}")
    old_pos = dict(node.position)

    await fm.move_node(flow_id, node_id, pos["x"], pos["y"])

    try:
        hm = get_app_context().history_manager
        await hm.record_operation(flow_id, "node.move",
                            forward={"node_id": node_id, "position": pos},
                            reverse={"node_id": node_id, "position": old_pos})
    except RuntimeError as e:
        logger.debug(f"History manager unavailable: {e}")

    await _send_ack(websocket, flow_id, msg_id)
    await _get_broadcast_to_flow()(flow_id, "node.moved", {
        "node_id": node_id, "position": pos,
    })
    await _get_push_history_state()(websocket, flow_id)


async def handle_node_update_config(websocket: WebSocket, flow_id: str, msg_id: str,
                                    params: dict) -> None:
    fm = get_app_context().flow_manager
    node_id = params["node_id"]
    new_config = params.get("config", {})

    flow = fm.load_flow(flow_id)
    node = flow.get_node(node_id)
    if not node:
        raise ValueError(f"Node not found: {node_id}")
    old_config = dict(node.config)

    await fm.update_node_config(flow_id, node_id, new_config)

    try:
        hm = get_app_context().history_manager
        await hm.record_operation(flow_id, "node.update_config",
                            forward={"node_id": node_id, "config": new_config},
                            reverse={"node_id": node_id, "config": old_config})
    except RuntimeError as e:
        logger.debug(f"History manager unavailable: {e}")

    await _send_ack(websocket, flow_id, msg_id)
    await _get_broadcast_to_flow()(flow_id, "node.config_updated", {
        "node_id": node_id,
        "config": fm.load_flow(flow_id).get_node(node_id).config,
    })
    await _get_push_history_state()(websocket, flow_id)


async def handle_node_rename(websocket: WebSocket, flow_id: str, msg_id: str,
                             params: dict) -> None:
    fm = get_app_context().flow_manager
    node_id = params["node_id"]
    new_name = params["name"]

    flow = fm.load_flow(flow_id)
    node = flow.get_node(node_id)
    if not node:
        raise ValueError(f"Node not found: {node_id}")
    old_name = node.name

    await fm.rename_node(flow_id, node_id, new_name)

    try:
        hm = get_app_context().history_manager
        await hm.record_operation(flow_id, "node.rename",
                            forward={"node_id": node_id, "name": new_name},
                            reverse={"node_id": node_id, "name": old_name})
    except RuntimeError as e:
        logger.debug(f"History manager unavailable: {e}")

    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "node.renamed", {
        "node_id": node_id, "name": new_name,
    })
    await _get_push_history_state()(websocket, flow_id)


# ── 连线 CRUD ──────────────────────────────────────────────────

async def handle_port_move(websocket: WebSocket, flow_id: str, msg_id: str,
                           params: dict) -> None:
    fm = get_app_context().flow_manager
    node_id = params["node_id"]
    port_id = params["port_id"]
    side = params["side"]
    position = params["position"]

    flow = fm.load_flow(flow_id)
    node = flow.get_node(node_id)
    if not node:
        raise ValueError(f"Node not found: {node_id}")

    port_positions = node.config.setdefault("_port_positions", {})
    port_positions[port_id] = {"side": side, "top": position}

    await fm.update_node_config(flow_id, node_id, {"_port_positions": port_positions})

    await _send_ack(websocket, flow_id, msg_id)
    await _get_broadcast_to_flow()(flow_id, "port.moved", {
        "node_id": node_id,
        "port_id": port_id,
        "side": side,
        "position": position,
    })


async def handle_connection_create(websocket: WebSocket, flow_id: str, msg_id: str,
                                   params: dict) -> None:
    fm = get_app_context().flow_manager
    from_node = params["from_node"]
    from_port = params["from_port"]
    to_node = params["to_node"]
    to_port = params["to_port"]
    conn_type = params.get("type", "data")

    if conn_type not in ("data", "event"):
        await _send_error(websocket, flow_id, "INVALID_TYPE", f"Invalid connection type: {conn_type!r}", msg_id)
        return

    err = fm.validate_connection(flow_id, from_node, from_port, to_node, to_port)
    if err:
        await _send_error(websocket, flow_id, "CONNECTION_INVALID", err, msg_id)
        return

    if fm.would_create_cycle(flow_id, from_node, to_node):
        await _send_error(websocket, flow_id, "CONNECTION_INVALID",
                          "Connection would create a cycle", msg_id)
        return

    conn_id = f"conn_{uuid.uuid4().hex[:8]}"
    conn = ConnectionDef(
        id=conn_id,
        from_node=from_node, from_port=from_port,
        to_node=to_node, to_port=to_port,
        type=conn_type,
    )
    await fm.add_connection(flow_id, conn)

    # 连线 → 执行系统桥接
    flow = fm.load_flow(flow_id)
    target = flow.get_node(to_node)
    if target:
        if conn_type == "event":
            target.trigger = TriggerConfig(
                type="on_complete",
                source_node=from_node,
            )
            await fm.save_flow(flow)
        elif conn_type == "data":
            as_field = port_input_key(to_port)
            source_field = port_output_key(from_port)
            mapping = InputMapping(
                from_node=from_node,
                as_field=as_field,
                source_field=source_field,
            )
            if not any(m.from_node == from_node and m.as_field == as_field
                       for m in target.input_mappings):
                target.input_mappings.append(mapping)
                await fm.save_flow(flow)

    try:
        hm = get_app_context().history_manager
        await hm.record_operation(flow_id, "connection.create",
                            forward={"connection_id": conn_id},
                            reverse={"connection_id": conn_id})
    except RuntimeError as e:
        logger.debug(f"History manager unavailable: {e}")

    await _send_ack(websocket, flow_id, msg_id)
    conn_data = fm._serialize_flow(fm.load_flow(flow_id))["connections"][-1]
    await _get_broadcast_to_flow()(flow_id, "connection.created", {"connection": conn_data})
    await _get_push_history_state()(websocket, flow_id)


async def handle_connection_delete(websocket: WebSocket, flow_id: str, msg_id: str,
                                   params: dict) -> None:
    fm = get_app_context().flow_manager
    conn_id = params["connection_id"]

    flow = fm.load_flow(flow_id)
    saved_conn = None
    for c in fm._serialize_flow(flow)["connections"]:
        if c["id"] == conn_id:
            saved_conn = c
            break

    if saved_conn:
        target = flow.get_node(saved_conn["to_node"])
        if target:
            if saved_conn.get("type") == "event":
                if target.trigger and target.trigger.source_node == saved_conn["from_node"]:
                    target.trigger = None
            elif saved_conn.get("type") == "data":
                as_field = port_input_key(saved_conn.get("to_port", ""))
                target.input_mappings = [
                    m for m in target.input_mappings
                    if not (m.from_node == saved_conn["from_node"] and m.as_field == as_field)
                ]
        await fm.save_flow(flow)

    await fm.remove_connection(flow_id, conn_id)

    try:
        hm = get_app_context().history_manager
        await hm.record_operation(flow_id, "connection.delete",
                            forward={"connection_id": conn_id},
                            reverse={"connection": saved_conn})
    except RuntimeError as e:
        logger.debug(f"History manager unavailable: {e}")

    await _send_ack(websocket, flow_id, msg_id)
    await _get_broadcast_to_flow()(flow_id, "connection.deleted", {"connection_id": conn_id})
    await _get_push_history_state()(websocket, flow_id)


# ── 撤销/重做 ──────────────────────────────────────────────────

async def handle_undo(websocket: WebSocket, flow_id: str, msg_id: str,
                      params: dict) -> None:
    hm = get_app_context().history_manager
    op = await hm.undo(flow_id)

    if not op:
        await _send_ack(websocket, flow_id, msg_id)
        await _get_push_history_state()(websocket, flow_id)
        return

    fm = get_app_context().flow_manager
    await _apply_reverse(fm, flow_id, op)

    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.loaded", {
        "flow": fm._serialize_flow(fm.load_flow(flow_id)),
    })
    await _get_push_history_state()(websocket, flow_id)


async def handle_redo(websocket: WebSocket, flow_id: str, msg_id: str,
                      params: dict) -> None:
    hm = get_app_context().history_manager
    op = await hm.redo(flow_id)

    if not op:
        await _send_ack(websocket, flow_id, msg_id)
        await _get_push_history_state()(websocket, flow_id)
        return

    fm = get_app_context().flow_manager
    await _apply_forward(fm, flow_id, op)

    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.loaded", {
        "flow": fm._serialize_flow(fm.load_flow(flow_id)),
    })
    await _get_push_history_state()(websocket, flow_id)


async def _apply_reverse(fm, flow_id: str, op: dict) -> None:
    action = op["action"]
    rev = op["reverse"]

    if action == "node.create":
        await fm.remove_node(flow_id, rev["node_id"])
    elif action == "node.delete":
        node_data = rev.get("node")
        if node_data:
            await fm.add_node(flow_id, fm._deserialize_node(node_data))
    elif action == "node.move":
        await fm.move_node(flow_id, rev["node_id"], rev["position"]["x"], rev["position"]["y"])
    elif action == "node.update_config":
        await fm.update_node_config(flow_id, rev["node_id"], rev["config"])
    elif action == "node.rename":
        await fm.rename_node(flow_id, rev["node_id"], rev["name"])
    elif action == "connection.create":
        await fm.remove_connection(flow_id, rev["connection_id"])
    elif action == "connection.delete":
        conn_data = rev.get("connection")
        if conn_data:
            await fm.add_connection(flow_id, ConnectionDef(
                id=conn_data["id"], from_node=conn_data["from_node"],
                from_port=conn_data["from_port"], to_node=conn_data["to_node"],
                to_port=conn_data["to_port"], type=conn_data.get("type", "data"),
            ))


async def _apply_forward(fm, flow_id: str, op: dict) -> None:
    action = op["action"]
    fwd = op["forward"]

    if action == "node.create":
        from core.pipeline.registry import NodeRegistry
        type_def = NodeRegistry.get_type_def(fwd.get("node_type", "ocr"))
        node = NodeDefinition(
            id=fwd["node_id"], type=fwd.get("node_type", "ocr"),
            name=type_def.name, position=fwd.get("position", {"x": 0, "y": 0}),
            config=dict(type_def.default_config),
        )
        await fm.add_node(flow_id, node)
    elif action == "node.delete":
        await fm.remove_node(flow_id, fwd["node_id"])
    elif action == "node.move":
        await fm.move_node(flow_id, fwd["node_id"], fwd["position"]["x"], fwd["position"]["y"])
    elif action == "node.update_config":
        await fm.update_node_config(flow_id, fwd["node_id"], fwd["config"])
    elif action == "node.rename":
        await fm.rename_node(flow_id, fwd["node_id"], fwd["name"])
    elif action == "connection.create":
        await fm.add_connection(flow_id, ConnectionDef(
            id=fwd["connection_id"], from_node=fwd.get("from_node", ""),
            from_port=fwd.get("from_port", ""), to_node=fwd.get("to_node", ""),
            to_port=fwd.get("to_port", ""), type=fwd.get("type", "data"),
        ))
    elif action == "connection.delete":
        await fm.remove_connection(flow_id, fwd["connection_id"])


# ── 配置持久化 ──────────────────────────────────────────────────

async def handle_config_get_default(websocket: WebSocket, flow_id: str, msg_id: str,
                                    params: dict) -> None:
    scope = params.get("scope", "node")
    target_id = params.get("target_id")
    dm = get_app_context().defaults_manager
    config = dm.load_default(scope, target_id)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "config.default", {
        "scope": scope, "target_id": target_id, "config": config,
    })


async def handle_config_save_default(websocket: WebSocket, flow_id: str, msg_id: str,
                                     params: dict) -> None:
    scope = params.get("scope", "node")
    target_id = params.get("target_id")
    config = params.get("config", {})
    dm = get_app_context().defaults_manager
    dm.save_default(scope, target_id, config)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "config.saved", {
        "scope": scope, "target_id": target_id,
    })


# ── 命令映射表 ──────────────────────────────────────────────────

COMMAND_HANDLERS = {
    # 节点 CRUD
    "node.create": handle_node_create,
    "node.delete": handle_node_delete,
    "node.move": handle_node_move,
    "node.update_config": handle_node_update_config,
    "node.rename": handle_node_rename,
    # 端口
    "port.move": handle_port_move,
    # 连线 CRUD
    "connection.create": handle_connection_create,
    "connection.delete": handle_connection_delete,
    # 撤销/重做
    "undo": handle_undo,
    "redo": handle_redo,
    # 配置
    "config.get_default": handle_config_get_default,
    "config.save_default": handle_config_save_default,
}
