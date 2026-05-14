"""
流程 CRUD 命令处理器

处理 flow.* 系列命令：流程的增删改查、分组管理、导入导出。
从 ws_main.py 拆分，共享工具函数通过 import 引用。
"""

import base64
import logging
from datetime import datetime, timezone

from fastapi import WebSocket

from core.app_context import get_app_context
from api.routes.ws_utils import _send, _send_ack

logger = logging.getLogger(__name__)


def _get_broadcast_to_flow():
    from api.routes.ws_main import _broadcast_to_flow
    return _broadcast_to_flow

def _get_broadcast_sidebar_tree():
    from api.routes.ws_main import _broadcast_sidebar_tree
    return _broadcast_sidebar_tree

def _get_subscribe_flow():
    from api.routes.ws_main import _subscribe_flow
    return _subscribe_flow


# ── 命令处理器 ──────────────────────────────────────────────────

async def handle_flow_list(websocket: WebSocket, flow_id: str, msg_id: str,
                           params: dict) -> None:
    fm = get_app_context().flow_manager
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
    fm = get_app_context().flow_manager
    target_flow_id = params.get("flow_id", flow_id)
    if not target_flow_id:
        raise ValueError("Missing required param: flow_id")
    flow = fm.load_flow(target_flow_id)
    flow_data = fm._serialize_flow(flow)
    await _get_subscribe_flow()(websocket, target_flow_id)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, target_flow_id, "event", "flow.loaded", {"flow": flow_data})


async def handle_flow_create(websocket: WebSocket, flow_id: str, msg_id: str,
                             params: dict) -> None:
    fm = get_app_context().flow_manager
    name = params.get("name", "Untitled")
    group = params.get("group", "")
    icon = params.get("icon", "account_tree")
    flow = fm.create_flow(name, group, icon)
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
    await _get_broadcast_sidebar_tree()(websocket)


async def handle_flow_delete(websocket: WebSocket, flow_id: str, msg_id: str,
                             params: dict) -> None:
    fm = get_app_context().flow_manager
    target_flow_id = params.get("flow_id", flow_id)
    await fm.delete_flow(target_flow_id)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.deleted", {"flow_id": target_flow_id})
    await _get_broadcast_sidebar_tree()(websocket)


async def handle_flow_rename(websocket: WebSocket, flow_id: str, msg_id: str,
                             params: dict) -> None:
    fm = get_app_context().flow_manager
    target_flow_id = params.get("flow_id", flow_id)
    new_name = params["name"]
    flow = fm.load_flow(target_flow_id)
    flow.name = new_name
    await fm.save_flow(flow)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.renamed", {
        "flow_id": target_flow_id, "name": new_name,
    })
    await _get_broadcast_sidebar_tree()(websocket)


async def handle_flow_copy(websocket: WebSocket, flow_id: str, msg_id: str,
                           params: dict) -> None:
    fm = get_app_context().flow_manager
    target_flow_id = params.get("flow_id", flow_id)
    new_name = params.get("name")
    flow = await fm.copy_flow(target_flow_id, new_name)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.copied", {
        "flow": {
            "id": flow.id, "name": flow.name, "group": flow.group,
            "icon": flow.icon, "node_count": len(flow.nodes),
            "enabled": flow.enabled,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    })
    await _get_broadcast_sidebar_tree()(websocket)


async def handle_flow_update_group(websocket: WebSocket, flow_id: str, msg_id: str,
                                    params: dict) -> None:
    fm = get_app_context().flow_manager
    target_flow_id = params.get("flow_id", flow_id)
    group = params.get("group", "")
    flow = await fm.update_flow_group(target_flow_id, group)
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
    await _get_broadcast_sidebar_tree()(websocket)


async def handle_flow_rename_group(websocket: WebSocket, flow_id: str, msg_id: str,
                                    params: dict) -> None:
    fm = get_app_context().flow_manager
    old_path = params["old_path"]
    new_path = params["new_path"]
    count = await fm.rename_group(old_path, new_path)
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
    await _get_broadcast_sidebar_tree()(websocket)


async def handle_flow_delete_group(websocket: WebSocket, flow_id: str, msg_id: str,
                                    params: dict) -> None:
    fm = get_app_context().flow_manager
    group_path = params["group_path"]
    count = await fm.delete_flows_in_group(group_path)
    fm.remove_group(group_path)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.group_deleted", {
        "group_path": group_path, "count": count,
    })
    await _get_broadcast_sidebar_tree()(websocket)


async def handle_flow_update(websocket: WebSocket, flow_id: str, msg_id: str,
                              params: dict) -> None:
    fm = get_app_context().flow_manager
    if "canvas" in params:
        await fm.update_flow_canvas(flow_id, params["canvas"])
    if "params" in params:
        await fm.update_flow_params(flow_id, params["params"])
    if "delete_param" in params:
        await fm.delete_flow_param(flow_id, params["delete_param"])
    await _send_ack(websocket, flow_id, msg_id)
    if "params" in params or "delete_param" in params:
        flow = fm.load_flow(flow_id)
        await _get_broadcast_to_flow()(flow_id, "flow.params_updated", {
            "flow_id": flow_id,
            "params": flow.params,
        })


async def handle_flow_create_group(websocket: WebSocket, flow_id: str, msg_id: str,
                                    params: dict) -> None:
    fm = get_app_context().flow_manager
    group_path = params["group_path"]
    fm.create_group(group_path)
    await _send_ack(websocket, flow_id, msg_id)
    await _get_broadcast_sidebar_tree()(websocket)


async def handle_flow_toggle_enabled(websocket: WebSocket, flow_id: str, msg_id: str,
                                      params: dict) -> None:
    fm = get_app_context().flow_manager
    target_flow_id = params.get("flow_id", flow_id)
    flow = await fm.toggle_flow_enabled(target_flow_id)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.enabled_toggled", {
        "flow_id": target_flow_id, "enabled": flow.enabled,
    })
    await _get_broadcast_sidebar_tree()(websocket)


async def handle_flow_export(websocket: WebSocket, flow_id: str, msg_id: str,
                              params: dict) -> None:
    fm = get_app_context().flow_manager
    target_flow_id = params.get("flow_id", flow_id)
    data = fm.export_flow(target_flow_id)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.exported", {
        "flow_id": target_flow_id, "data": data,
    })


async def handle_flow_import(websocket: WebSocket, flow_id: str, msg_id: str,
                              params: dict) -> None:
    fm = get_app_context().flow_manager
    data = params["data"]
    overwrite = params.get("overwrite", False)
    flow = await fm.import_flow(data, overwrite)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.imported", {
        "flow": {
            "id": flow.id, "name": flow.name, "group": flow.group,
            "icon": flow.icon, "node_count": len(flow.nodes),
            "enabled": flow.enabled,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    })
    await _get_broadcast_sidebar_tree()(websocket)


async def handle_flow_export_group(websocket: WebSocket, flow_id: str, msg_id: str,
                                    params: dict) -> None:
    fm = get_app_context().flow_manager
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
    fm = get_app_context().flow_manager
    b64 = params["data_b64"]
    target_group = params.get("group", "")
    overwrite = params.get("overwrite", False)
    zip_bytes = base64.b64decode(b64)
    imported = await fm.import_group_zip(zip_bytes, target_group, overwrite)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "flow.group_imported", {
        "group": target_group,
        "count": len(imported),
    })
    await _get_broadcast_sidebar_tree()(websocket)


# ── 命令映射表 ──────────────────────────────────────────────────

COMMAND_HANDLERS = {
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
}
