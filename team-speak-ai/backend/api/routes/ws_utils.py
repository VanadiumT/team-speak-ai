"""WebSocket 信封协议工具函数

纯函数，无状态，无循环依赖风险。
ws_main.py 和 ws_presets.py 共用。
"""

import json
import uuid
from datetime import datetime, timezone

from fastapi import WebSocket


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
