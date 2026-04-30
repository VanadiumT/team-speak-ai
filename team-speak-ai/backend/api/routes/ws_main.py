"""
统一 WebSocket 端点 —— /ws

单一连接承载流程管理、节点编辑、文件上传、配置持久化、执行状态推送。
协议遵循 docs/websocket-protocol.md 信封格式。

Phase 1: 连接生命周期 + 流程只读命令
"""

import json
import uuid
import logging
import asyncio
import time
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.pipeline.registry import NodeRegistry
from core.pipeline.definition import NodeDefinition, ConnectionDef
from core.flow.manager import get_flow_manager
from core.history.manager import get_history_manager
from core.config.defaults import get_defaults_manager

logger = logging.getLogger(__name__)

router = APIRouter()

HEARTBEAT_TIMEOUT = 90  # seconds without activity before disconnect
WS_MAX_MSG_SIZE = 64 * 1024  # 64KB max text message size

# 已连接的客户端
_connected_clients: dict[str, WebSocket] = {}
_flow_subscribers: dict[str, set[WebSocket]] = {}
_client_last_activity: dict[str, float] = {}  # client_id → last activity timestamp (seconds)


# ── 工具函数 ───────────────────────────────────────────────────

def _now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _make_msg(flow_id: str, type_: str, action: str, params: dict = None,
              ref_msg_id: str = None) -> dict:
    msg = {
        "msg_id": str(uuid.uuid4()),
        "flow_id": flow_id,
        "type": type_,
        "action": action,
        "params": params or {},
        "ts": _now_ts(),
    }
    if ref_msg_id:
        msg["ref_msg_id"] = ref_msg_id
    return msg


async def _send(ws: WebSocket, flow_id: str, type_: str, action: str,
                params: dict = None, ref_msg_id: str = None) -> str:
    msg = _make_msg(flow_id, type_, action, params, ref_msg_id)
    await ws.send_text(json.dumps(msg, ensure_ascii=False))
    return msg["msg_id"]


async def _send_ack(ws: WebSocket, flow_id: str, ref_msg_id: str) -> None:
    await _send(ws, flow_id, "ack", "ack", {"ok": True}, ref_msg_id)


async def _send_error(ws: WebSocket, flow_id: str, code: str, message: str,
                      ref_msg_id: str = None) -> None:
    await _send(ws, flow_id, "error", "error", {
        "code": code,
        "message": message,
    }, ref_msg_id)


# ── 连接生命周期 ───────────────────────────────────────────────

@router.websocket("/ws")
async def ws_main(websocket: WebSocket):
    await websocket.accept()
    client_id = str(uuid.uuid4())
    _connected_clients[client_id] = websocket
    _client_last_activity[client_id] = time.time()
    logger.info(f"WS client connected: {client_id}")

    async def heartbeat_monitor():
        """断开长时间无活动的客户端"""
        try:
            while True:
                await asyncio.sleep(15)
                if _client_last_activity.get(client_id, 0) < time.time() - HEARTBEAT_TIMEOUT:
                    logger.info(f"WS client heartbeat timeout: {client_id}")
                    try:
                        await websocket.close(code=1001, reason="heartbeat timeout")
                    except Exception:
                        pass
                    return
        except asyncio.CancelledError:
            pass

    monitor_task = asyncio.create_task(heartbeat_monitor())

    try:
        # 下发初始元数据
        flow_id = "_system"  # 系统级消息使用特殊 flow_id

        # 1. 节点类型列表
        types = NodeRegistry.list_type_defs()
        types_data = []
        for t in types:
            types_data.append({
                "type": t.type,
                "name": t.name,
                "icon": t.icon,
                "color": t.color,
                "default_config": t.default_config,
                "tabs": [{"id": tb.id, "label": tb.label} for tb in t.tabs],
                "ports": {
                    "inputs": [
                        {"id": p.id, "label": p.label, "data_type": p.data_type,
                         "position": {"side": p.position.side, "top": p.position.top}}
                        for p in t.ports.inputs
                    ],
                    "outputs": [
                        {"id": p.id, "label": p.label, "data_type": p.data_type,
                         "position": {"side": p.position.side, "top": p.position.top}}
                        for p in t.ports.outputs
                    ],
                },
            })
        await _send(websocket, flow_id, "event", "node_types", {"types": types_data})

        # 2. 侧栏树
        fm = get_flow_manager()
        tree = fm.build_sidebar_tree()
        tree_data = [_sidebar_node_to_dict(n) for n in tree]
        await _send(websocket, flow_id, "event", "sidebar.tree", {"groups": tree_data})

        # 3. 服务连接状态
        await _broadcast_connection_status(websocket, flow_id)

        # 消息循环（文本 + 二进制帧）
        while True:
            _client_last_activity[client_id] = time.time()
            data = await websocket.receive()

            if data["type"] == "websocket.disconnect":
                break

            if "text" in data:
                # 处理 ping 消息
                if data["text"].strip() == "ping":
                    await websocket.send_text("pong")
                    continue
                if len(data["text"]) > WS_MAX_MSG_SIZE:
                    await _send_error(websocket, "_system", "MESSAGE_TOO_LARGE",
                                      f"Message exceeds {WS_MAX_MSG_SIZE} bytes limit")
                    continue
                try:
                    msg = json.loads(data["text"])
                except json.JSONDecodeError:
                    await _send_error(websocket, "_system", "INVALID_PARAMS", "Invalid JSON")
                    continue

                msg_type = msg.get("type", "")
                if msg_type == "command":
                    await _handle_command(websocket, msg)

            elif "bytes" in data:
                await _handle_binary_frame(websocket, data["bytes"])

    except WebSocketDisconnect:
        logger.info(f"WS client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WS error for client {client_id}: {e}")
    finally:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        _connected_clients.pop(client_id, None)
        _client_last_activity.pop(client_id, None)
        _unsubscribe_all_flows(websocket)


# ── 二进制帧处理 ───────────────────────────────────────────────

async def _handle_binary_frame(websocket: WebSocket, data: bytes) -> None:
    """处理二进制帧（文件上传数据块）"""
    from core.upload.chunk_receiver import ChunkReceiver, get_chunk_receiver

    try:
        msg_id, chunk = ChunkReceiver.parse_binary_frame(data)
        cr = get_chunk_receiver()
        session = cr.get_session_by_msg_id(msg_id)

        if not session:
            logger.warning(f"Binary frame for unknown upload: {msg_id}")
            return

        received = cr.receive_chunk(msg_id, chunk)

        # 发送进度（每 5 个 chunk 发一次，减少消息量）
        if received >= session.size or received % (256 * 1024 * 5) == 0:
            await _send(websocket, "_system", "event", "file.upload_progress", {
                "upload_id": session.upload_id,
                "received": received,
                "total": session.size,
            })

        # 上传完成
        if received >= session.size:
            result = cr.complete_upload(msg_id)
            await _send(websocket, "_system", "event", "file.upload_done", result)

    except ValueError as e:
        logger.warning(f"Binary frame parse error: {e}")


# ── 命令分发 ───────────────────────────────────────────────────

async def _handle_command(websocket: WebSocket, msg: dict) -> None:
    action = msg.get("action", "")
    flow_id = msg.get("flow_id", "_system")
    msg_id = msg.get("msg_id", "")

    handler = _COMMAND_HANDLERS.get(action)
    if not handler:
        await _send_error(websocket, flow_id, "UNKNOWN_ACTION",
                          f"Unknown action: {action}", msg_id)
        return

    try:
        params = msg.get("params", {})
        await handler(websocket, flow_id, msg_id, params)
    except FileNotFoundError as e:
        await _send_error(websocket, flow_id, "FLOW_NOT_FOUND", str(e), msg_id)
    except (ValueError, KeyError) as e:
        await _send_error(websocket, flow_id, "INVALID_PARAMS", str(e), msg_id)
    except Exception as e:
        logger.exception(f"Error handling command {action}")
        await _send_error(websocket, flow_id, "INTERNAL_ERROR", str(e), msg_id)


# ── Phase 1 命令处理器 ─────────────────────────────────────────

async def handle_flow_list(websocket: WebSocket, flow_id: str, msg_id: str,
                           params: dict) -> None:
    fm = get_flow_manager()
    flows = fm.list_flows()
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.list_result", {
        "flows": [
            {
                "id": f.id, "name": f.name, "group": f.group,
                "icon": f.icon, "node_count": f.node_count,
                "updated_at": f.updated_at,
            }
            for f in flows
        ],
    })


async def handle_flow_load(websocket: WebSocket, flow_id: str, msg_id: str,
                           params: dict) -> None:
    fm = get_flow_manager()
    target_flow_id = params.get("flow_id", flow_id)
    if not target_flow_id:
        raise ValueError("Missing required param: flow_id")
    flow = fm.load_flow(target_flow_id)
    flow_data = fm._serialize_flow(flow)
    # 订阅该 flow 的编辑事件
    await _subscribe_flow(websocket, target_flow_id)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, target_flow_id, "event", "flow.loaded", {"flow": flow_data})


async def handle_flow_create(websocket: WebSocket, flow_id: str, msg_id: str,
                             params: dict) -> None:
    fm = get_flow_manager()
    name = params.get("name", "Untitled")
    group = params.get("group", "")
    icon = params.get("icon", "account_tree")
    flow = fm.create_flow(name, group, icon)
    # 隐式持久化中间目录路径，使目录在删除所有流程后仍然保留
    if group:
        parts = [p.strip() for p in group.split("/") if p.strip()]
        acc = ""
        for part in parts:
            acc = acc + "/" + part if acc else part
            fm.create_group(acc)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.created", {
        "flow": {
            "id": flow.id, "name": flow.name, "group": flow.group,
            "icon": flow.icon, "node_count": 0,
            "enabled": flow.enabled,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    })
    await _broadcast_sidebar_tree(websocket)


async def handle_flow_delete(websocket: WebSocket, flow_id: str, msg_id: str,
                             params: dict) -> None:
    fm = get_flow_manager()
    target_flow_id = params.get("flow_id", flow_id)
    fm.delete_flow(target_flow_id)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.deleted", {"flow_id": target_flow_id})
    await _broadcast_sidebar_tree(websocket)


async def handle_flow_rename(websocket: WebSocket, flow_id: str, msg_id: str,
                             params: dict) -> None:
    fm = get_flow_manager()
    target_flow_id = params.get("flow_id", flow_id)
    new_name = params["name"]
    flow = fm.load_flow(target_flow_id)
    flow.name = new_name
    fm.save_flow(flow)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.renamed", {
        "flow_id": target_flow_id, "name": new_name,
    })
    await _broadcast_sidebar_tree(websocket)


async def handle_flow_copy(websocket: WebSocket, flow_id: str, msg_id: str,
                           params: dict) -> None:
    fm = get_flow_manager()
    target_flow_id = params.get("flow_id", flow_id)
    new_name = params.get("name")
    flow = fm.copy_flow(target_flow_id, new_name)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.copied", {
        "flow": {
            "id": flow.id, "name": flow.name, "group": flow.group,
            "icon": flow.icon, "node_count": len(flow.nodes),
            "enabled": flow.enabled,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    })
    await _broadcast_sidebar_tree(websocket)


async def handle_flow_update_group(websocket: WebSocket, flow_id: str, msg_id: str,
                                    params: dict) -> None:
    """移动流程到指定分组"""
    fm = get_flow_manager()
    target_flow_id = params.get("flow_id", flow_id)
    group = params.get("group", "")
    flow = fm.update_flow_group(target_flow_id, group)
    # 持久化目标目录路径
    if group:
        parts = [p.strip() for p in group.split("/") if p.strip()]
        acc = ""
        for part in parts:
            acc = acc + "/" + part if acc else part
            fm.create_group(acc)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.group_updated", {
        "flow_id": target_flow_id, "group": group,
    })
    await _broadcast_sidebar_tree(websocket)


async def handle_flow_rename_group(websocket: WebSocket, flow_id: str, msg_id: str,
                                    params: dict) -> None:
    """重命名分组（批量更新所有相关 flow 的 group 字段）"""
    fm = get_flow_manager()
    old_path = params["old_path"]
    new_path = params["new_path"]
    count = fm.rename_group(old_path, new_path)
    # 同步更新 groups.json 中的目录路径
    groups = fm.list_groups()
    updated_groups = []
    for g in groups:
        if g == old_path:
            updated_groups.append(new_path)
        elif g.startswith(old_path + "/"):
            updated_groups.append(new_path + g[len(old_path):])
        else:
            updated_groups.append(g)
    fm._save_groups(updated_groups)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.group_renamed", {
        "old_path": old_path, "new_path": new_path, "count": count,
    })
    await _broadcast_sidebar_tree(websocket)


async def handle_flow_delete_group(websocket: WebSocket, flow_id: str, msg_id: str,
                                    params: dict) -> None:
    """删除分组及其所有流程"""
    fm = get_flow_manager()
    group_path = params["group_path"]
    count = fm.delete_flows_in_group(group_path)
    fm.remove_group(group_path)  # 同时从 groups.json 中移除
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.group_deleted", {
        "group_path": group_path, "count": count,
    })
    await _broadcast_sidebar_tree(websocket)


async def handle_flow_update(websocket: WebSocket, flow_id: str, msg_id: str,
                              params: dict) -> None:
    """更新流程级设置（画布尺寸等）"""
    fm = get_flow_manager()
    if "canvas" in params:
        fm.update_flow_canvas(flow_id, params["canvas"])
    await _send_ack(websocket, flow_id, msg_id)


async def handle_flow_create_group(websocket: WebSocket, flow_id: str, msg_id: str,
                                    params: dict) -> None:
    """创建空目录（持久化到 groups.json）"""
    fm = get_flow_manager()
    group_path = params["group_path"]
    fm.create_group(group_path)
    await _send_ack(websocket, flow_id, msg_id)
    await _broadcast_sidebar_tree(websocket)


async def handle_flow_toggle_enabled(websocket: WebSocket, flow_id: str, msg_id: str,
                                      params: dict) -> None:
    """切换流程启用/禁用"""
    fm = get_flow_manager()
    target_flow_id = params.get("flow_id", flow_id)
    flow = fm.toggle_flow_enabled(target_flow_id)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.enabled_toggled", {
        "flow_id": target_flow_id, "enabled": flow.enabled,
    })
    await _broadcast_sidebar_tree(websocket)


async def handle_flow_export(websocket: WebSocket, flow_id: str, msg_id: str,
                              params: dict) -> None:
    """导出流程为 JSON"""
    fm = get_flow_manager()
    target_flow_id = params.get("flow_id", flow_id)
    data = fm.export_flow(target_flow_id)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.exported", {
        "flow_id": target_flow_id, "data": data,
    })


async def handle_flow_import(websocket: WebSocket, flow_id: str, msg_id: str,
                              params: dict) -> None:
    """导入流程 JSON"""
    fm = get_flow_manager()
    data = params["data"]
    overwrite = params.get("overwrite", False)
    flow = fm.import_flow(data, overwrite)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.imported", {
        "flow": {
            "id": flow.id, "name": flow.name, "group": flow.group,
            "icon": flow.icon, "node_count": len(flow.nodes),
            "enabled": flow.enabled,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    })
    await _broadcast_sidebar_tree(websocket)


async def handle_flow_export_group(websocket: WebSocket, flow_id: str, msg_id: str,
                                    params: dict) -> None:
    """导出分组为 ZIP（base64 编码）"""
    import base64
    fm = get_flow_manager()
    group_path = params.get("group_path", "")
    if group_path:
        zip_bytes = fm.export_group_zip(group_path)
        filename = group_path.replace("/", "_") + ".zip"
    else:
        zip_bytes = fm.export_all_zip()
        filename = "all_workflows.zip"
    b64 = base64.b64encode(zip_bytes).decode("ascii")
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.group_exported", {
        "group_path": group_path or "",
        "filename": filename,
        "data_b64": b64,
    })


async def handle_flow_import_group(websocket: WebSocket, flow_id: str, msg_id: str,
                                    params: dict) -> None:
    """从 ZIP 导入分组（base64 编码）"""
    import base64
    fm = get_flow_manager()
    b64 = params["data_b64"]
    target_group = params.get("group", "")
    overwrite = params.get("overwrite", False)
    zip_bytes = base64.b64decode(b64)
    imported = fm.import_group_zip(zip_bytes, target_group, overwrite)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.group_imported", {
        "group": target_group,
        "count": len(imported),
    })
    await _broadcast_sidebar_tree(websocket)


# ── Phase 2: 节点 CRUD ────────────────────────────────────────

async def handle_node_create(websocket: WebSocket, flow_id: str, msg_id: str,
                             params: dict) -> None:
    fm = get_flow_manager()
    node_type = params["node_type"]
    position = params.get("position", {"x": 0, "y": 0})

    from core.pipeline.registry import NodeRegistry
    type_def = NodeRegistry.get_type_def(node_type)

    node_id = f"{node_type}_{uuid.uuid4().hex[:6]}"
    node = NodeDefinition(
        id=node_id,
        type=node_type,
        name=type_def.name,
        position=position,
        config=dict(type_def.default_config),
    )
    await fm.add_node(flow_id, node)

    # 记录操作历史
    try:
        hm = get_history_manager()
        await hm.record_operation(flow_id, "node.create",
                            forward={"node_id": node_id, "node_type": node_type, "position": position},
                            reverse={"node_id": node_id})
    except RuntimeError:
        pass  # history manager not yet initialized

    await _send_ack(websocket, flow_id, msg_id)
    node_data = fm._serialize_flow(fm.load_flow(flow_id))["nodes"][-1]
    await _broadcast_to_flow(flow_id, "node.created", {"node": node_data})
    await _push_history_state(websocket, flow_id)


async def handle_node_delete(websocket: WebSocket, flow_id: str, msg_id: str,
                             params: dict) -> None:
    fm = get_flow_manager()
    node_id = params["node_id"]

    # 保存节点信息用于 undo
    flow = fm.load_flow(flow_id)
    node = flow.get_node(node_id)
    if not node:
        raise ValueError(f"Node not found: {node_id}")
    saved = fm._serialize_flow(flow)["nodes"]
    saved_node = next((n for n in saved if n["id"] == node_id), None)

    await fm.remove_node(flow_id, node_id)

    try:
        hm = get_history_manager()
        await hm.record_operation(flow_id, "node.delete",
                            forward={"node_id": node_id},
                            reverse={"node": saved_node})
    except RuntimeError:
        pass

    await _send_ack(websocket, flow_id, msg_id)
    await _broadcast_to_flow(flow_id, "node.deleted", {"node_id": node_id})
    await _push_history_state(websocket, flow_id)


async def handle_node_move(websocket: WebSocket, flow_id: str, msg_id: str,
                           params: dict) -> None:
    fm = get_flow_manager()
    node_id = params["node_id"]
    pos = params["position"]

    flow = fm.load_flow(flow_id)
    node = flow.get_node(node_id)
    if not node:
        raise ValueError(f"Node not found: {node_id}")
    old_pos = dict(node.position)

    await fm.move_node(flow_id, node_id, pos["x"], pos["y"])

    try:
        hm = get_history_manager()
        await hm.record_operation(flow_id, "node.move",
                            forward={"node_id": node_id, "position": pos},
                            reverse={"node_id": node_id, "position": old_pos})
    except RuntimeError:
        pass

    await _send_ack(websocket, flow_id, msg_id)
    await _broadcast_to_flow(flow_id, "node.moved", {
        "node_id": node_id, "position": pos,
    })
    await _push_history_state(websocket, flow_id)


async def handle_node_update_config(websocket: WebSocket, flow_id: str, msg_id: str,
                                    params: dict) -> None:
    fm = get_flow_manager()
    node_id = params["node_id"]
    new_config = params.get("config", {})

    flow = fm.load_flow(flow_id)
    node = flow.get_node(node_id)
    if not node:
        raise ValueError(f"Node not found: {node_id}")
    old_config = dict(node.config)

    await fm.update_node_config(flow_id, node_id, new_config)

    try:
        hm = get_history_manager()
        await hm.record_operation(flow_id, "node.update_config",
                            forward={"node_id": node_id, "config": new_config},
                            reverse={"node_id": node_id, "config": old_config})
    except RuntimeError:
        pass

    await _send_ack(websocket, flow_id, msg_id)
    await _broadcast_to_flow(flow_id, "node.config_updated", {
        "node_id": node_id,
        "config": fm.load_flow(flow_id).get_node(node_id).config,
    })
    await _push_history_state(websocket, flow_id)


async def handle_node_rename(websocket: WebSocket, flow_id: str, msg_id: str,
                             params: dict) -> None:
    fm = get_flow_manager()
    node_id = params["node_id"]
    new_name = params["name"]

    flow = fm.load_flow(flow_id)
    node = flow.get_node(node_id)
    if not node:
        raise ValueError(f"Node not found: {node_id}")
    old_name = node.name

    await fm.rename_node(flow_id, node_id, new_name)

    try:
        hm = get_history_manager()
        await hm.record_operation(flow_id, "node.rename",
                            forward={"node_id": node_id, "name": new_name},
                            reverse={"node_id": node_id, "name": old_name})
    except RuntimeError:
        pass

    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "node.renamed", {
        "node_id": node_id, "name": new_name,
    })
    await _push_history_state(websocket, flow_id)


# ── Phase 2: 连线 CRUD ────────────────────────────────────────

async def handle_port_move(websocket: WebSocket, flow_id: str, msg_id: str,
                           params: dict) -> None:
    """持久化端口位置调整"""
    fm = get_flow_manager()
    node_id = params["node_id"]
    port_id = params["port_id"]
    side = params["side"]
    position = params["position"]

    flow = fm.load_flow(flow_id)
    node = flow.get_node(node_id)
    if not node:
        raise ValueError(f"Node not found: {node_id}")

    # 端口位置覆盖存储在 node.config 中
    port_positions = node.config.setdefault("_port_positions", {})
    port_positions[port_id] = {"side": side, "top": position}

    await fm.update_node_config(flow_id, node_id, {"_port_positions": port_positions})

    await _send_ack(websocket, flow_id, msg_id)
    await _broadcast_to_flow(flow_id, "port.moved", {
        "node_id": node_id,
        "port_id": port_id,
        "side": side,
        "position": position,
    })


async def handle_connection_create(websocket: WebSocket, flow_id: str, msg_id: str,
                                   params: dict) -> None:
    fm = get_flow_manager()
    from_node = params["from_node"]
    from_port = params["from_port"]
    to_node = params["to_node"]
    to_port = params["to_port"]
    conn_type = params.get("type", "data")

    # 校验
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

    try:
        hm = get_history_manager()
        await hm.record_operation(flow_id, "connection.create",
                            forward={"connection_id": conn_id},
                            reverse={"connection_id": conn_id})
    except RuntimeError:
        pass

    await _send_ack(websocket, flow_id, msg_id)
    conn_data = fm._serialize_flow(fm.load_flow(flow_id))["connections"][-1]
    await _broadcast_to_flow(flow_id, "connection.created", {"connection": conn_data})
    await _push_history_state(websocket, flow_id)


async def handle_connection_delete(websocket: WebSocket, flow_id: str, msg_id: str,
                                   params: dict) -> None:
    fm = get_flow_manager()
    conn_id = params["connection_id"]

    flow = fm.load_flow(flow_id)
    saved_conn = None
    for c in fm._serialize_flow(flow)["connections"]:
        if c["id"] == conn_id:
            saved_conn = c
            break

    await fm.remove_connection(flow_id, conn_id)

    try:
        hm = get_history_manager()
        await hm.record_operation(flow_id, "connection.delete",
                            forward={"connection_id": conn_id},
                            reverse={"connection": saved_conn})
    except RuntimeError:
        pass

    await _send_ack(websocket, flow_id, msg_id)
    await _broadcast_to_flow(flow_id, "connection.deleted", {"connection_id": conn_id})
    await _push_history_state(websocket, flow_id)


# ── Phase 2: 撤销/重做 ────────────────────────────────────────

async def handle_undo(websocket: WebSocket, flow_id: str, msg_id: str,
                      params: dict) -> None:
    hm = get_history_manager()
    op = await hm.undo(flow_id)

    if not op:
        await _send_ack(websocket, flow_id, msg_id)
        await _push_history_state(websocket, flow_id)
        return

    fm = get_flow_manager()
    await _apply_reverse(fm, flow_id, op)

    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.loaded", {
        "flow": fm._serialize_flow(fm.load_flow(flow_id)),
    })
    await _push_history_state(websocket, flow_id)


async def handle_redo(websocket: WebSocket, flow_id: str, msg_id: str,
                      params: dict) -> None:
    hm = get_history_manager()
    op = await hm.redo(flow_id)

    if not op:
        await _send_ack(websocket, flow_id, msg_id)
        await _push_history_state(websocket, flow_id)
        return

    fm = get_flow_manager()
    await _apply_forward(fm, flow_id, op)

    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.loaded", {
        "flow": fm._serialize_flow(fm.load_flow(flow_id)),
    })
    await _push_history_state(websocket, flow_id)


async def _apply_reverse(fm, flow_id: str, op: dict) -> None:
    """应用撤销操作"""
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
            from core.pipeline.definition import ConnectionDef as CD
            await fm.add_connection(flow_id, CD(
                id=conn_data["id"], from_node=conn_data["from_node"],
                from_port=conn_data["from_port"], to_node=conn_data["to_node"],
                to_port=conn_data["to_port"], type=conn_data.get("type", "data"),
            ))


async def _apply_forward(fm, flow_id: str, op: dict) -> None:
    """应用重做操作"""
    action = op["action"]
    fwd = op["forward"]

    if action == "node.create":
        node_data = fwd
        from core.pipeline.registry import NodeRegistry
        type_def = NodeRegistry.get_type_def(fwd.get("node_type", "ocr"))
        node = NodeDefinition(
            id=fwd["node_id"], type=fwd.get("node_type", "ocr"),
            name=type_def.name, position=fwd.get("position", {"x": 0, "y": 0}),
            config=dict(type_def.default_config),
        )
        await fm.add_node(flow_id, node)
    elif action == "node.delete":
        flow = fm.load_flow(flow_id)
        await fm.remove_node(flow_id, fwd["node_id"])
    elif action == "node.move":
        await fm.move_node(flow_id, fwd["node_id"], fwd["position"]["x"], fwd["position"]["y"])
    elif action == "node.update_config":
        await fm.update_node_config(flow_id, fwd["node_id"], fwd["config"])
    elif action == "node.rename":
        await fm.rename_node(flow_id, fwd["node_id"], fwd["name"])
    elif action == "connection.create":
        from core.pipeline.definition import ConnectionDef as CD
        conn_data = fwd
        await fm.add_connection(flow_id, CD(
            id=fwd["connection_id"], from_node=fwd.get("from_node", ""),
            from_port=fwd.get("from_port", ""), to_node=fwd.get("to_node", ""),
            to_port=fwd.get("to_port", ""), type=fwd.get("type", "data"),
        ))
    elif action == "connection.delete":
        await fm.remove_connection(flow_id, fwd["connection_id"])


# ── Phase 2: 配置持久化 ───────────────────────────────────────

async def handle_config_get_default(websocket: WebSocket, flow_id: str, msg_id: str,
                                    params: dict) -> None:
    scope = params.get("scope", "node")
    target_id = params.get("target_id")
    dm = get_defaults_manager()
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
    dm = get_defaults_manager()
    dm.save_default(scope, target_id, config)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "config.saved", {
        "scope": scope, "target_id": target_id,
    })


# ── Phase 3: 执行控制 ────────────────────────────────────────

async def handle_pipeline_run(websocket: WebSocket, flow_id: str, msg_id: str,
                              params: dict) -> None:
    """启动 Pipeline 执行"""
    from core.pipeline.engine import engine

    if engine.is_running(flow_id):
        await _send_error(websocket, flow_id, "PIPELINE_RUNNING",
                          "Pipeline is already running", msg_id)
        return

    # 编辑锁：拒绝正在执行的流程编辑
    execution_id = engine.start_pipeline_from_flow(flow_id)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "pipeline.started", {
        "execution_id": execution_id,
    })


async def handle_pipeline_stop(websocket: WebSocket, flow_id: str, msg_id: str,
                               params: dict) -> None:
    """停止 Pipeline 执行"""
    from core.pipeline.engine import engine

    execution_id = params.get("execution_id", "")
    if execution_id:
        engine.delete_instance(execution_id)
    else:
        # 停止该 flow 的所有执行
        for inst in engine.list_instances(flow_id):
            engine.delete_instance(inst.execution_id)

    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "pipeline.stopped", {
        "execution_id": execution_id or flow_id,
    })


async def handle_node_trigger(websocket: WebSocket, flow_id: str, msg_id: str,
                              params: dict) -> None:
    """手动触发节点执行"""
    from core.pipeline.engine import engine

    node_id = params["node_id"]
    instances = engine.list_instances(flow_id)
    if not instances:
        execution_id = engine.start_pipeline_from_flow(flow_id)
    else:
        execution_id = instances[-1].execution_id

    await engine.execute_node(execution_id, node_id)
    await _send_ack(websocket, flow_id, msg_id)


# ── Phase 3: 文件上传 ────────────────────────────────────────

async def handle_file_upload_start(websocket: WebSocket, flow_id: str, msg_id: str,
                                   params: dict) -> None:
    """发起文件上传请求"""
    from core.upload.chunk_receiver import get_chunk_receiver

    cr = get_chunk_receiver()
    result = cr.start_upload(
        msg_id=msg_id,
        name=params["name"],
        size=params["size"],
        mime_type=params.get("mime_type", "application/octet-stream"),
        node_id=params.get("node_id"),
        received=params.get("received", 0),
    )
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "file.upload_ready", result)


async def handle_file_upload_cancel(websocket: WebSocket, flow_id: str, msg_id: str,
                                    params: dict) -> None:
    """取消文件上传"""
    from core.upload.chunk_receiver import get_chunk_receiver

    cr = get_chunk_receiver()
    cr.cancel_upload(params["upload_id"])
    await _send_ack(websocket, flow_id, msg_id)


# ── 命令路由表 ─────────────────────────────────────────────────

_COMMAND_HANDLERS = {
    # Phase 1: 流程管理
    "flow.list": handle_flow_list,
    "flow.load": handle_flow_load,
    "flow.create": handle_flow_create,
    "flow.delete": handle_flow_delete,
    "flow.rename": handle_flow_rename,
    "flow.copy": handle_flow_copy,
    "flow.update_group": handle_flow_update_group,
    "flow.rename_group": handle_flow_rename_group,
    "flow.delete_group": handle_flow_delete_group,
    "flow.update": handle_flow_update,
    "flow.create_group": handle_flow_create_group,
    "flow.toggle_enabled": handle_flow_toggle_enabled,
    "flow.export": handle_flow_export,
    "flow.import": handle_flow_import,
    "flow.export_group": handle_flow_export_group,
    "flow.import_group": handle_flow_import_group,
    # Phase 2: 节点 CRUD
    "node.create": handle_node_create,
    "node.delete": handle_node_delete,
    "node.move": handle_node_move,
    "node.update_config": handle_node_update_config,
    "node.rename": handle_node_rename,
    # Phase 2: 端口
    "port.move": handle_port_move,
    # Phase 2: 连线 CRUD
    "connection.create": handle_connection_create,
    "connection.delete": handle_connection_delete,
    # Phase 2: 撤销/重做
    "undo": handle_undo,
    "redo": handle_redo,
    # Phase 2: 配置
    "config.get_default": handle_config_get_default,
    "config.save_default": handle_config_save_default,
    # Phase 3: 执行控制
    "pipeline.run": handle_pipeline_run,
    "pipeline.stop": handle_pipeline_stop,
    "node.trigger": handle_node_trigger,
    # Phase 3: 文件上传
    "file.upload_start": handle_file_upload_start,
    "file.upload_cancel": handle_file_upload_cancel,
}


# ── 状态广播 ───────────────────────────────────────────────────

async def _broadcast_connection_status(websocket: WebSocket, flow_id: str) -> None:
    """发送当前各服务的连接状态"""
    try:
        from api.routes.ws_teamspeak import ts_client
        from core.pipeline.engine import engine
        from config import settings

        services = [
            {
                "id": "ts_bot",
                "name": "TeamSpeakBot 服务",
                "status": "connected" if ts_client.connected else "disconnected",
                "detail": settings.ts_ws_url,
            },
            {
                "id": "backend",
                "name": "TeamSpeakAI 后端",
                "status": "healthy",
                "detail": "0.1.0",
            },
            {
                "id": "pipeline",
                "name": "Pipeline",
                "status": "listening" if engine.active_instance_count > 0 else "healthy",
                "detail": "就绪" if engine.active_instance_count == 0 else f"{engine.active_instance_count} 实例运行中",
            },
        ]
    except Exception:
        services = [
            {"id": "backend", "name": "TeamSpeakAI 后端", "status": "healthy", "detail": "0.1.0"},
        ]

    await _send(websocket, flow_id, "event", "connection.status", {"services": services})


async def broadcast_connection_status_to_all() -> None:
    """向所有已连接客户端广播连接状态"""
    services = []
    try:
        from api.routes.ws_teamspeak import ts_client
        from config import settings
        services = [
            {
                "id": "ts_bot",
                "name": "TeamSpeakBot 服务",
                "status": "connected" if ts_client.connected else "disconnected",
                "detail": settings.ts_ws_url,
            },
            {"id": "backend", "name": "TeamSpeakAI 后端", "status": "healthy", "detail": "0.1.0"},
            {"id": "pipeline", "name": "Pipeline", "status": "healthy", "detail": "就绪"},
        ]
    except Exception:
        services = [
            {"id": "backend", "name": "TeamSpeakAI 后端", "status": "healthy", "detail": "0.1.0"},
        ]

    for ws in list(_connected_clients.values()):
        try:
            await _send(ws, "_system", "event", "connection.status", {"services": services})
        except Exception:
            pass


# ── Flow 订阅管理 ─────────────────────────────────────────────

async def _subscribe_flow(websocket: WebSocket, flow_id: str) -> None:
    """订阅某个 flow 的编辑事件"""
    if flow_id not in _flow_subscribers:
        _flow_subscribers[flow_id] = set()
    _flow_subscribers[flow_id].add(websocket)


def _unsubscribe_flow(websocket: WebSocket, flow_id: str) -> None:
    """取消订阅"""
    if flow_id in _flow_subscribers:
        _flow_subscribers[flow_id].discard(websocket)


def _unsubscribe_all_flows(websocket: WebSocket) -> None:
    """取消所有订阅（连接断开时调用）"""
    for flow_id in list(_flow_subscribers.keys()):
        _flow_subscribers[flow_id].discard(websocket)


async def _broadcast_to_flow(flow_id: str, action: str, params: dict) -> None:
    """向订阅了某个 flow 的所有连接广播事件（并发编辑）"""
    subs = _flow_subscribers.get(flow_id, set())
    for ws in list(subs):
        try:
            await _send(ws, flow_id, "event", action, params)
        except Exception:
            pass


async def _ws_flow_broadcast(flow_id: str, action: str, params: dict) -> None:
    """Engine 回调：向 /ws 端点的 flow 订阅者广播执行事件"""
    subs = _flow_subscribers.get(flow_id, set())
    for ws in list(subs):
        try:
            await _send(ws, flow_id, "event", action, params)
        except Exception:
            pass


def _register_engine_broadcast():
    """注册 engine 的 flow 广播回调"""
    from core.pipeline.engine import engine
    engine.register_flow_broadcast_fn("__all__", _ws_flow_broadcast)


_register_engine_broadcast()


async def _broadcast_sidebar_tree(websocket: WebSocket) -> None:
    """刷新当前连接的侧栏树"""
    fm = get_flow_manager()
    tree = fm.build_sidebar_tree()
    tree_data = [_sidebar_node_to_dict(n) for n in tree]
    await _send(websocket, "_system", "event", "sidebar.tree", {"groups": tree_data})


async def _push_history_state(websocket: WebSocket, flow_id: str) -> None:
    """推送当前流程的 undo/redo 状态"""
    try:
        hm = get_history_manager()
        state = hm.history_state(flow_id)
        await _send(websocket, flow_id, "event", "history.state", state)
    except RuntimeError:
        pass


# ── 侧栏序列化 ─────────────────────────────────────────────────

def _sidebar_node_to_dict(node) -> dict:
    from core.pipeline.definition import SidebarNode as SNode
    d = {
        "id": node.id,
        "name": node.name,
        "icon": node.icon,
        "type": node.type,
    }
    if node.flow_id:
        d["flow_id"] = node.flow_id
        d["enabled"] = node.enabled
    if node.children:
        d["children"] = [_sidebar_node_to_dict(c) for c in node.children]
    return d
