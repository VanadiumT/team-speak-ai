"""
执行控制、文件上传、通知、系统变量命令处理器

处理 pipeline.*、file.*、notification.*、sys_var.* 系列命令。
从 ws_main.py 拆分，共享工具函数通过 import 引用。
"""

import logging

from fastapi import WebSocket

from core.app_context import get_app_context
from api.routes.ws_utils import _send, _send_ack, _send_error

logger = logging.getLogger(__name__)


def _get_broadcast_to_flow():
    from api.routes.ws_main import _broadcast_to_flow
    return _broadcast_to_flow


# ── 执行控制 ──────────────────────────────────────────────────

async def handle_pipeline_run(websocket: WebSocket, flow_id: str, msg_id: str,
                              params: dict) -> None:
    if get_app_context().pipeline_engine.is_running(flow_id):
        await _send_error(websocket, flow_id, "PIPELINE_RUNNING",
                          "Pipeline is already running", msg_id)
        return

    execution_id = await get_app_context().pipeline_engine.start_pipeline_from_flow(flow_id)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "pipeline.started", {
        "execution_id": execution_id,
    })


async def handle_pipeline_stop(websocket: WebSocket, flow_id: str, msg_id: str,
                               params: dict) -> None:
    execution_id = params.get("execution_id", "")
    if execution_id:
        get_app_context().pipeline_engine.delete_instance(execution_id)
    else:
        for inst in get_app_context().pipeline_engine.list_instances(flow_id):
            get_app_context().pipeline_engine.delete_instance(inst.execution_id)

    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "pipeline.stopped", {
        "execution_id": execution_id or flow_id,
    })


async def handle_node_trigger(websocket: WebSocket, flow_id: str, msg_id: str,
                              params: dict) -> None:
    node_id = params["node_id"]
    instances = get_app_context().pipeline_engine.list_instances(flow_id)
    if not instances:
        execution_id = await get_app_context().pipeline_engine.start_pipeline_from_flow(flow_id)
    else:
        execution_id = instances[-1].execution_id

    user_input = params.get("payload", None)
    await get_app_context().pipeline_engine.execute_node(execution_id, node_id, user_input=user_input)
    await _send_ack(websocket, flow_id, msg_id)


# ── 文件上传 ──────────────────────────────────────────────────

async def handle_file_upload_start(websocket: WebSocket, flow_id: str, msg_id: str,
                                   params: dict) -> None:
    cr = get_app_context().chunk_receiver
    result = cr.start_upload(
        msg_id=msg_id,
        name=params["name"],
        size=params["size"],
        mime_type=params.get("mime_type", "application/octet-stream"),
        node_id=params.get("node_id"),
        flow_id=flow_id,
        received=params.get("received", 0),
    )
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, flow_id, "event", "file.upload_ready", result)


async def handle_file_upload_cancel(websocket: WebSocket, flow_id: str, msg_id: str,
                                    params: dict) -> None:
    cr = get_app_context().chunk_receiver
    cr.cancel_upload(params["upload_id"])
    await _send_ack(websocket, flow_id, msg_id)


# ── 通知 ─────────────────────────────────────────────────────

async def handle_notification_list(websocket: WebSocket, flow_id: str, msg_id: str,
                                   params: dict) -> None:
    nm = get_app_context().notification_manager
    target_flow_id = params.get("flow_id", flow_id)
    limit = params.get("limit", 20)
    before = params.get("before")
    result = nm.list_notifications(target_flow_id, limit, before)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, target_flow_id, "event", "notification.list_result", result)


async def handle_notification_mark_read(websocket: WebSocket, flow_id: str, msg_id: str,
                                        params: dict) -> None:
    nm = get_app_context().notification_manager
    target_flow_id = params.get("flow_id", flow_id)
    notification_id = params.get("notification_id")
    unread = nm.mark_read(target_flow_id, notification_id)
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, target_flow_id, "event", "notification.read", {
        "notification_id": notification_id,
        "unread": unread,
    })


# ── 系统变量 ──────────────────────────────────────────────────

async def handle_sys_var_list(websocket: WebSocket, flow_id: str, msg_id: str,
                               params: dict) -> None:
    svm = get_app_context().sys_var_manager
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, "_system", "event", "sys_var.list_result", {
        "vars": svm.list_all(),
    })


async def handle_sys_var_get(websocket: WebSocket, flow_id: str, msg_id: str,
                              params: dict) -> None:
    key = params.get("key", "")
    svm = get_app_context().sys_var_manager
    await _send_ack(websocket, flow_id, msg_id)
    await _send(websocket, "_system", "event", "sys_var.get_result", {
        "key": key,
        "value": svm.get(key),
    })


async def handle_sys_var_set(websocket: WebSocket, flow_id: str, msg_id: str,
                              params: dict) -> None:
    key = params.get("key", "")
    value = params.get("value")
    merge_mode = params.get("merge_mode", "overwrite")
    if not key:
        await _send_error(websocket, flow_id, "INVALID_KEY", "key is required", msg_id)
        return
    svm = get_app_context().sys_var_manager
    svm.set(key, value, merge_mode)
    await _send_ack(websocket, flow_id, msg_id)
    await _get_broadcast_to_flow()("__all__", "sys_var.updated", {"key": key, "value": value})


async def handle_sys_var_delete(websocket: WebSocket, flow_id: str, msg_id: str,
                                 params: dict) -> None:
    key = params.get("key", "")
    if not key:
        await _send_error(websocket, flow_id, "INVALID_KEY", "key is required", msg_id)
        return
    svm = get_app_context().sys_var_manager
    svm.delete(key)
    await _send_ack(websocket, flow_id, msg_id)
    await _get_broadcast_to_flow()("__all__", "sys_var.deleted", {"key": key})


# ── 命令映射表 ──────────────────────────────────────────────────

COMMAND_HANDLERS = {
    # 执行控制
    "pipeline.run": handle_pipeline_run,
    "pipeline.stop": handle_pipeline_stop,
    "node.trigger": handle_node_trigger,
    # 文件上传
    "file.upload_start": handle_file_upload_start,
    "file.upload_cancel": handle_file_upload_cancel,
    # 通知
    "notification.list": handle_notification_list,
    "notification.mark_read": handle_notification_mark_read,
    # 系统变量
    "sys_var.list": handle_sys_var_list,
    "sys_var.get": handle_sys_var_get,
    "sys_var.set": handle_sys_var_set,
    "sys_var.delete": handle_sys_var_delete,
}
