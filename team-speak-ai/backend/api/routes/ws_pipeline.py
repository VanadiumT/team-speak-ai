"""
Pipeline WebSocket 端点 — 取代旧的 ws_client.py

一个连接，多路复用多个 feature 订阅。
前端通过此端点：
- 获取功能页配置 (get_config)
- 订阅/取消订阅某个 feature 的实时事件
- 发送节点操作 (node_action: upload / trigger / restart / input_text)
"""

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.pipeline.engine import engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["pipeline"])


@router.websocket("/pipeline")
async def pipeline_websocket(websocket: WebSocket):
    """Pipeline 实时通信端点"""
    await websocket.accept()
    subscribed: set[str] = set()

    logger.info("Pipeline WS connected")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")
            msg_data = msg.get("data", {})

            if msg_type == "subscribe":
                fid = msg_data.get("feature_id", "")
                if fid:
                    engine.register_ws(fid, websocket)
                    subscribed.add(fid)

                    # 如果已有运行中的 instance，推送当前状态
                    instances = engine.list_instances(fid)
                    if instances:
                        inst = instances[-1]
                        rt_list = [
                            {
                                "node_id": nid,
                                "status": rt.status.value,
                                "summary": rt.summary,
                                "progress": rt.progress,
                                "error": rt.error,
                                "data": rt.data,
                            }
                            for nid, rt in inst.node_runtimes.items()
                        ]
                        await websocket.send_json({
                            "type": "pipeline_state",
                            "data": {
                                "feature_id": fid,
                                "execution_id": inst.execution_id,
                                "status": inst.status,
                                "nodes": rt_list,
                            },
                        })
                    await websocket.send_json({
                        "type": "subscribed",
                        "data": {"feature_id": fid},
                    })

            elif msg_type == "unsubscribe":
                fid = msg_data.get("feature_id", "")
                if fid:
                    engine.unregister_ws(fid, websocket)
                    subscribed.discard(fid)

            elif msg_type == "get_config":
                configs = engine.get_definitions()
                await websocket.send_json({
                    "type": "feature_config",
                    "data": configs,
                })

            elif msg_type == "node_action":
                await engine.handle_node_action(msg_data)

    except WebSocketDisconnect:
        logger.info("Pipeline WS disconnected")
    except Exception as e:
        logger.error(f"Pipeline WS error: {e}")
    finally:
        # 清理所有订阅
        engine.unregister_ws_all(websocket)
