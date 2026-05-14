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
from core.app_context import get_app_context
from api.routes.ws_utils import _now_ts, _make_msg, _send, _send_ack, _send_error
from api.routes.ws_presets import make_preset_handlers, handle_preset_test_llm, handle_tts_preset_test, handle_stt_preset_test, handle_ocr_preset_test, handle_ts_preset_test
from api.routes.ws_flow import COMMAND_HANDLERS as _FLOW_HANDLERS
from api.routes.ws_editor import COMMAND_HANDLERS as _EDITOR_HANDLERS
from api.routes.ws_exec import COMMAND_HANDLERS as _EXEC_HANDLERS

logger = logging.getLogger(__name__)

router = APIRouter()

from config import settings as _settings
HEARTBEAT_TIMEOUT = _settings.ws_heartbeat_timeout  # seconds without activity before disconnect
WS_MAX_MSG_SIZE = _settings.ws_max_msg_size  # max text message size (bytes)

# WS 订阅层级说明：
# 1. _connected_clients — 所有已连接的 WS 客户端（client_id → WebSocket）
# 2. _flow_subscribers — 按 flow_id 分组的客户端订阅（flow_id → {ws, ...}）
#
# 广播路径：pipeline_engine.broadcast_to_flow() → 调用注册的 _broadcast_to_flow() →
# 遍历 _flow_subscribers[flow_id] 发送事件。engine 层不直接持有前端 WS。
_connected_clients: dict[str, WebSocket] = {}
_flow_subscribers: dict[str, set[WebSocket]] = {}
_client_last_activity: dict[str, float] = {}  # client_id → last activity timestamp (seconds)


# ── 工具函数（从 ws_utils 导入）───────────────────────────────
# _now_ts, _make_msg, _send, _send_ack, _send_error 已在顶部从 ws_utils 导入

# ── 连接生命周期 ───────────────────────────────────────────────

@router.websocket("/ws")
async def ws_main(websocket: WebSocket):
    # ── Token 鉴权 ──
    from config import settings
    if settings.ws_auth_token:
        token = websocket.query_params.get("token", "")
        if token != settings.ws_auth_token:
            await websocket.close(code=4001, reason="Unauthorized")
            return

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

        # 0. 订阅全局广播通道（接收 presets / sys_var 等全局更新）
        await _subscribe_flow(websocket, "__all__")

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
                         "visibility": getattr(p, 'visibility', 'always') or 'always',
                         "repeatable": getattr(p, 'repeatable', False) or False,
                         "group": getattr(p, 'group', None) or None,
                         "min": getattr(p, 'min', None) or None,
                         "max": getattr(p, 'max', None) or None,
                         "position": {"side": p.position.side, "top": p.position.top}}
                        for p in t.ports.inputs
                    ],
                    "outputs": [
                        {"id": p.id, "label": p.label, "data_type": p.data_type,
                         "visibility": getattr(p, 'visibility', 'always') or 'always',
                         "repeatable": getattr(p, 'repeatable', False) or False,
                         "group": getattr(p, 'group', None) or None,
                         "min": getattr(p, 'min', None) or None,
                         "max": getattr(p, 'max', None) or None,
                         "position": {"side": p.position.side, "top": p.position.top}}
                        for p in t.ports.outputs
                    ],
                },
            })
        await _send(websocket, flow_id, "event", "node_types", {"types": types_data})

        # 2. 预设广播（敏感字段脱敏）
        from api.routes.ws_presets import mask_presets_data
        ctx = get_app_context()
        await _send(websocket, flow_id, "event", "presets.list", mask_presets_data(ctx.preset_manager.list_all()))
        await _send(websocket, flow_id, "event", "stt_presets.list", mask_presets_data(ctx.stt_preset_manager.list_all()))
        await _send(websocket, flow_id, "event", "tts_presets.list", mask_presets_data(ctx.tts_preset_manager.list_all()))
        await _send(websocket, flow_id, "event", "ocr_presets.list", mask_presets_data(ctx.ocr_preset_manager.list_all()))
        await _send(websocket, flow_id, "event", "ts_presets.list", mask_presets_data(ctx.ts_preset_manager.list_all()))
        await _send(websocket, flow_id, "event", "vad_presets.list", mask_presets_data(ctx.vad_preset_manager.list_all()))

        # 3. 侧栏树
        fm = ctx.flow_manager
        tree = fm.build_sidebar_tree()
        tree_data = [_sidebar_node_to_dict(n) for n in tree]
        await _send(websocket, flow_id, "event", "sidebar.tree", {"groups": tree_data})

        # 4. 服务连接状态
        await _broadcast_connection_status(websocket, flow_id)

        # 5. 通知未读计数
        nm = get_app_context().notification_manager
        tree = fm.build_sidebar_tree()
        for fid in _collect_flow_ids(tree):
            count = nm.get_unread_count(fid)
            if count > 0:
                await _send(websocket, "_system", "event", "notification.unread", {
                    "flow_id": fid,
                    "unread": count,
                })

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
    from core.upload.chunk_receiver import ChunkReceiver

    try:
        msg_id, chunk = ChunkReceiver.parse_binary_frame(data)
        cr = get_app_context().chunk_receiver
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
            filepath = session.filepath
            flow_id = session.flow_id
            node_id = session.node_id
            result = cr.complete_upload(msg_id)
            await _send(websocket, "_system", "event", "file.upload_done", result)

            # 自动触发目标节点继续流程
            if flow_id and node_id:
                import base64
                with open(filepath, "rb") as f:
                    file_bytes = f.read()
                b64_data = base64.b64encode(file_bytes).decode("ascii")
                file_payload = {
                    "data": b64_data,
                    "filename": result["name"],
                    "mime_type": result["mime_type"],
                }
                
                if not get_app_context().pipeline_engine.is_running(flow_id):
                    logger.info(f"Upload complete but flow {flow_id} is not running, skip auto-trigger")
                else:
                    execution_ids = [
                        eid for eid, inst in get_app_context().pipeline_engine._instances.items()
                        if inst.pipeline_def.id == flow_id
                    ]
                    if execution_ids:
                        await get_app_context().pipeline_engine.execute_node(
                            execution_ids[0], node_id,
                            user_input={"file": file_payload},
                        )

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


# ── 命令注册表（合并各子模块的处理器）──────────────────────────────

_COMMAND_HANDLERS = {
    **_FLOW_HANDLERS,
    **_EDITOR_HANDLERS,
    **_EXEC_HANDLERS,
    **make_preset_handlers(),
    "preset.test_llm": handle_preset_test_llm,
    "tts_preset.test": handle_tts_preset_test,
    "stt_preset.test": handle_stt_preset_test,
    "ocr_preset.test": handle_ocr_preset_test,
    "ts_preset.test": handle_ts_preset_test,
}



# ── 状态广播 ───────────────────────────────────────────────────

async def _broadcast_connection_status(websocket: WebSocket, flow_id: str) -> None:
    """发送当前各服务的连接状态"""
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
            {
                "id": "backend",
                "name": "TeamSpeakAI 后端",
                "status": "healthy",
                "detail": "0.1.0",
            },
            {
                "id": "pipeline",
                "name": "Pipeline",
                "status": "listening" if get_app_context().pipeline_engine.active_instance_count > 0 else "healthy",
                "detail": "就绪" if get_app_context().pipeline_engine.active_instance_count == 0 else f"{get_app_context().pipeline_engine.active_instance_count} 实例运行中",
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
    """向订阅了某个 flow 的所有连接广播事件。
    同时作为 engine 的广播回调，接收 pipeline 执行事件并转发给前端订阅者。"""
    subs = _flow_subscribers.get(flow_id, set())
    for ws in list(subs):
        try:
            await _send(ws, flow_id, "event", action, params)
        except Exception:
            pass


def _register_engine_broadcast():
    """注册 engine 的 flow 广播回调（模块导入时执行，直接使用模块级 engine 单例）"""
    from core.pipeline.engine import engine
    engine.register_flow_broadcast_fn("__all__", _broadcast_to_flow)


_register_engine_broadcast()


async def _broadcast_sidebar_tree(websocket: WebSocket) -> None:
    """刷新当前连接的侧栏树"""
    fm = get_app_context().flow_manager
    tree = fm.build_sidebar_tree()
    tree_data = [_sidebar_node_to_dict(n) for n in tree]
    await _send(websocket, "_system", "event", "sidebar.tree", {"groups": tree_data})


async def _push_history_state(websocket: WebSocket, flow_id: str) -> None:
    """推送当前流程的 undo/redo 状态"""
    try:
        hm = get_app_context().history_manager
        state = hm.history_state(flow_id)
        await _send(websocket, flow_id, "event", "history.state", state)
    except RuntimeError:
        pass


# ── 侧栏工具 ──────────────────────────────────────────────────

def _collect_flow_ids(nodes) -> list[str]:
    """递归收集侧栏树中所有 flow_id"""
    result = []
    for node in nodes:
        if node.flow_id:
            result.append(node.flow_id)
        if node.children:
            result.extend(_collect_flow_ids(node.children))
    return result


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
