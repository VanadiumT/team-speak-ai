"""
预设 CRUD 路由处理器 (LLM / TTS / STT / OCR / VAD / TeamSpeak Bridge)

工厂模式：6 套预设的 list/save_platform/delete_platform/duplicate_platform/
save_model/delete_model/duplicate_model 由 make_preset_handlers() 统一生成。
连通性测试处理器因逻辑差异较大，保持独立实现。
"""

import json
import logging
import re
import socket
import asyncio as _asyncio

from fastapi import WebSocket
from core.app_context import get_app_context
from api.routes.ws_utils import _now_ts, _make_msg, _send, _send_ack

logger = logging.getLogger(__name__)


# ── 敏感字段脱敏 ──────────────────────────────────────────────

_SENSITIVE_FIELDS = {"api_key", "api_url"}


def _mask_value(key: str, value: str) -> str:
    """对单个敏感字段值脱敏。空值不处理，短值直接 *** ，长值保留前4后2。"""
    if not value or not isinstance(value, str):
        return value
    if key == "api_url":
        # URL 只掩 host 后的部分，保留协议+域名
        # ws://localhost:8080/teamspeak/voice → ws://localhost:8080/***
        if "://" in value:
            scheme_host, _, path = value.partition("://")
            parts = path.split("/", 1)
            if len(parts) > 1 and parts[1]:
                return f"{scheme_host}://{parts[0]}/***"
        return value
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***{value[-2:]}"


def mask_presets_data(data: dict) -> dict:
    """对预设数据中的敏感字段脱敏，返回新 dict（不修改原数据）"""
    from copy import deepcopy
    data = deepcopy(data)
    for platform in data.get("platforms", []):
        for field in _SENSITIVE_FIELDS:
            if field in platform and platform[field]:
                platform[field] = _mask_value(field, platform[field])
    return data


# ═══════════════════════════════════════════════════════════════════
# Preset 注册表
# ═══════════════════════════════════════════════════════════════════

_PRESET_TYPES = [
    # (command_prefix, manager_getter_import_path, list_event_name)
    ("preset",     "core.config.presets.llm", "presets.list"),
    ("tts_preset", "core.config.presets.tts", "tts_presets.list"),
    ("stt_preset", "core.config.presets.stt", "stt_presets.list"),
    ("ocr_preset", "core.config.presets.ocr", "ocr_presets.list"),
    ("vad_preset", "core.config.presets.vad", "vad_presets.list"),
    ("ts_preset",  "core.config.presets.ts",  "ts_presets.list"),
]


def _get_broadcast():
    """延迟导入 _broadcast_to_flow 避免循环依赖"""
    from api.routes.ws_main import _broadcast_to_flow
    return _broadcast_to_flow


def make_preset_handlers() -> dict:
    """工厂函数：为所有注册的预设类型生成 CRUD handler 字典

    返回 { "preset.list": handler, "preset.save_platform": handler, ... }
    """
    handlers = {}

    for cmd_prefix, module_path, event_name in _PRESET_TYPES:

        # ── 从 AppContext 获取对应的 preset manager ──
        def _get_manager(cp=cmd_prefix):
            """返回对应类型的 preset manager 实例"""
            ctx = get_app_context()
            if cp == "preset":
                return ctx.preset_manager
            elif cp == "tts_preset":
                return ctx.tts_preset_manager
            elif cp == "stt_preset":
                return ctx.stt_preset_manager
            elif cp == "ocr_preset":
                return ctx.ocr_preset_manager
            elif cp == "vad_preset":
                return ctx.vad_preset_manager
            elif cp == "ts_preset":
                return ctx.ts_preset_manager
            raise RuntimeError(f"Unknown preset type: {cp}")

        # ── list ──
        def make_list(ev=event_name, gf=_get_manager):
            async def handler(ws: WebSocket, flow_id: str, msg_id: str, params: dict):
                pm = gf()
                await _send_ack(ws, flow_id, msg_id)
                await _send(ws, "_system", "event", ev, mask_presets_data(pm.list_all()))
            return handler

        handlers[f"{cmd_prefix}.list"] = make_list()

        # ── save_platform ──
        def make_save_plat(ev=event_name, gf=_get_manager):
            async def handler(ws: WebSocket, flow_id: str, msg_id: str, params: dict):
                pm = gf()
                platform = params.get("platform", {})
                data = pm.save_platform(platform)
                await _send_ack(ws, flow_id, msg_id)
                await _get_broadcast()("__all__", ev, mask_presets_data(data))
            return handler

        handlers[f"{cmd_prefix}.save_platform"] = make_save_plat()

        # ── delete_platform ──
        def make_del_plat(ev=event_name, gf=_get_manager):
            async def handler(ws: WebSocket, flow_id: str, msg_id: str, params: dict):
                pm = gf()
                platform_id = params["platform_id"]
                data = pm.delete_platform(platform_id)
                await _send_ack(ws, flow_id, msg_id)
                await _get_broadcast()("__all__", ev, mask_presets_data(data))
            return handler

        handlers[f"{cmd_prefix}.delete_platform"] = make_del_plat()

        # ── duplicate_platform ──
        def make_dup_plat(ev=event_name, gf=_get_manager):
            async def handler(ws: WebSocket, flow_id: str, msg_id: str, params: dict):
                pm = gf()
                platform_id = params["platform_id"]
                data = pm.duplicate_platform(platform_id)
                await _send_ack(ws, flow_id, msg_id)
                await _get_broadcast()("__all__", ev, mask_presets_data(data))
            return handler

        handlers[f"{cmd_prefix}.duplicate_platform"] = make_dup_plat()

        # ── save_model ──
        def make_save_mdl(ev=event_name, gf=_get_manager):
            async def handler(ws: WebSocket, flow_id: str, msg_id: str, params: dict):
                pm = gf()
                platform_id = params["platform_id"]
                model = params.get("model", {})
                data = pm.save_model(platform_id, model)
                await _send_ack(ws, flow_id, msg_id)
                await _get_broadcast()("__all__", ev, mask_presets_data(data))
            return handler

        handlers[f"{cmd_prefix}.save_model"] = make_save_mdl()

        # ── delete_model ──
        def make_del_mdl(ev=event_name, gf=_get_manager):
            async def handler(ws: WebSocket, flow_id: str, msg_id: str, params: dict):
                pm = gf()
                platform_id = params["platform_id"]
                model_id = params["model_id"]
                data = pm.delete_model(platform_id, model_id)
                await _send_ack(ws, flow_id, msg_id)
                await _get_broadcast()("__all__", ev, mask_presets_data(data))
            return handler

        handlers[f"{cmd_prefix}.delete_model"] = make_del_mdl()

        # ── duplicate_model ──
        def make_dup_mdl(ev=event_name, gf=_get_manager):
            async def handler(ws: WebSocket, flow_id: str, msg_id: str, params: dict):
                pm = gf()
                platform_id = params["platform_id"]
                model_id = params["model_id"]
                data = pm.duplicate_model(platform_id, model_id)
                await _send_ack(ws, flow_id, msg_id)
                await _get_broadcast()("__all__", ev, mask_presets_data(data))
            return handler

        handlers[f"{cmd_prefix}.duplicate_model"] = make_dup_mdl()

    return handlers


# ═══════════════════════════════════════════════════════════════════
# 连通性测试处理器（逻辑差异较大，保持独立实现）
# ═══════════════════════════════════════════════════════════════════

async def handle_preset_test_llm(websocket: WebSocket, flow_id: str, msg_id: str,
                                  params: dict) -> None:
    pm = get_app_context().preset_manager
    platform_id = params["platform_id"]
    model_id = params["model_id"]
    result = {}
    try:
        config = pm.get_effective_config(platform_id, model_id)
        from core.llm.openai_llm import OpenAILLM
        llm = OpenAILLM(
            api_key=config["api_key"], base_url=config["base_url"],
            model=config["model"], temperature=config.get("temperature"),
            max_tokens=min(config.get("max_tokens") or 128, 128),
            top_p=config.get("top_p"),
        )
        resp = await llm.chat([{"role": "user", "content": "Say just 'OK'."}])
        result = {"type": "llm", "platform_id": platform_id, "model_id": model_id,
                  "success": True, "message": "连接成功", "detail": resp.content[:300]}
    except Exception as e:
        logger.warning(f"LLM test failed: {e}")
        result = {"type": "llm", "platform_id": platform_id, "model_id": model_id,
                  "success": False, "message": f"测试失败: {str(e)[:300]}", "detail": ""}
    await _send(websocket, flow_id, "ack", "ack", {"ok": True, "test_result": result}, msg_id)


async def handle_tts_preset_test(websocket: WebSocket, flow_id: str, msg_id: str,
                                  params: dict) -> None:
    pm = get_app_context().tts_preset_manager
    platform_id = params["platform_id"]
    model_id = params["model_id"]
    result = {}
    try:
        config = pm.get_effective_config(platform_id, model_id)
        from core.tts.factory import create_tts, TTSProvider
        provider = TTSProvider(config["provider"])
        if provider == TTSProvider.EDGE:
            tts_params = {"voice": config.get("voice_id", "zh-CN-XiaoxiaoNeural")}
        else:
            tts_params = {
                "api_key": config["api_key"], "model": config["model"],
                "voice_id": config["voice_id"], "speed": config["speed"],
                "vol": config["vol"], "pitch": config["pitch"],
                "sample_rate": config.get("sample_rate", 32000),
                "bitrate": config.get("bitrate", 128000),
                "file_format": config.get("format", "mp3"),
                "channel": config.get("channel", 1),
            }
            if config.get("emotion"):
                tts_params["emotion"] = config["emotion"]
            if config.get("language_boost"):
                tts_params["language_boost"] = config["language_boost"]
        tts = create_tts(provider, tts_params)
        audio = await tts.synthesize("测试语音")
        result = {"type": "tts", "platform_id": platform_id, "model_id": model_id,
                  "success": True, "message": "合成成功",
                  "detail": f"生成 {len(audio)} 字节音频"}
    except Exception as e:
        logger.warning(f"TTS test failed: {e}")
        result = {"type": "tts", "platform_id": platform_id, "model_id": model_id,
                  "success": False, "message": f"测试失败: {str(e)[:300]}", "detail": ""}
    await _send(websocket, flow_id, "ack", "ack", {"ok": True, "test_result": result}, msg_id)


async def handle_stt_preset_test(websocket: WebSocket, flow_id: str, msg_id: str,
                                  params: dict) -> None:
    pm = get_app_context().stt_preset_manager
    platform_id = params["platform_id"]
    model_id = params["model_id"]
    result = {}
    try:
        config = pm.get_effective_config(platform_id, model_id)
        from core.stt.factory import create_stt, STTProvider
        provider = STTProvider(config["provider"])
        if provider == STTProvider.SENSEVOICE:
            stt_params = {"model_dir": config["model_dir"],
                           "device": config.get("device", "cpu")}
        elif provider == STTProvider.WHISPER:
            stt_params = {"model_name": config.get("model_name", "base"),
                           "device": config.get("device", "cuda")}
        else:
            stt_params = {"api_key": config["api_key"],
                           "api_url": config.get("api_url") or "https://api.minimax.chat/v1"}
        stt = create_stt(provider, stt_params)
        result = {"type": "stt", "platform_id": platform_id, "model_id": model_id,
                  "success": True, "message": "配置有效，实例创建成功",
                  "detail": f"Provider: {config['provider']}"}
    except Exception as e:
        logger.warning(f"STT test failed: {e}")
        result = {"type": "stt", "platform_id": platform_id, "model_id": model_id,
                  "success": False, "message": f"测试失败: {str(e)[:300]}", "detail": ""}
    await _send(websocket, flow_id, "ack", "ack", {"ok": True, "test_result": result}, msg_id)


async def handle_ocr_preset_test(websocket: WebSocket, flow_id: str, msg_id: str,
                                  params: dict) -> None:
    pm = get_app_context().ocr_preset_manager
    platform_id = params["platform_id"]
    model_id = params["model_id"]
    result = {}
    try:
        config = pm.get_effective_config(platform_id, model_id)
        from core.ocr.factory import create_ocr, OCRProvider
        provider = OCRProvider(config["provider"])
        ocr_params = {}
        if provider == OCRProvider.EASYOCR:
            ocr_params = {"lang_list": config.get("lang_list", ["ch_sim", "en"]),
                           "gpu": config.get("gpu", False)}
        elif provider == OCRProvider.PADDLEOCR:
            ocr_params = {"lang": config.get("lang", "ch"),
                           "use_angle_cls": config.get("use_angle_cls", True),
                           "use_gpu": config.get("gpu", False),
                           "det_model_dir": config.get("det_model_dir") or None,
                           "rec_model_dir": config.get("rec_model_dir") or None}
        ocr = create_ocr(provider, ocr_params)
        result = {"type": "ocr", "platform_id": platform_id, "model_id": model_id,
                  "success": True, "message": "引擎初始化成功",
                  "detail": f"Provider: {config['provider']}"}
    except Exception as e:
        logger.warning(f"OCR test failed: {e}")
        result = {"type": "ocr", "platform_id": platform_id, "model_id": model_id,
                  "success": False, "message": f"测试失败: {str(e)[:300]}", "detail": ""}
    await _send(websocket, flow_id, "ack", "ack", {"ok": True, "test_result": result}, msg_id)


async def handle_ts_preset_test(websocket: WebSocket, flow_id: str, msg_id: str,
                                 params: dict) -> None:
    pm = get_app_context().ts_preset_manager
    platform_id = params["platform_id"]
    result = {}
    try:
        platform = pm.get_platform(platform_id)
        if not platform:
            result = {"type": "ts", "platform_id": platform_id,
                      "success": False, "message": "桥接实例不存在"}
            await _send(websocket, flow_id, "ack", "ack", {"ok": True, "test_result": result}, msg_id)
            return
        ws_url = platform.get("ws_url", "")
        if not ws_url:
            result = {"type": "ts", "platform_id": platform_id,
                      "success": False, "message": "未配置 ws_url"}
            await _send(websocket, flow_id, "ack", "ack", {"ok": True, "test_result": result}, msg_id)
            return
        m = re.match(r'ws://([^:/]+)(?::(\d+))?(/.*)?$', ws_url)
        if not m:
            result = {"type": "ts", "platform_id": platform_id,
                      "success": False, "message": f"无法解析 ws_url: {ws_url}"}
            await _send(websocket, flow_id, "ack", "ack", {"ok": True, "test_result": result}, msg_id)
            return
        host = m.group(1)
        port = int(m.group(2)) if m.group(2) else 8080
        loop = _asyncio.get_running_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        ret = await loop.run_in_executor(None, lambda: sock.connect_ex((host, port)))
        sock.close()
        if ret == 0:
            result = {"type": "ts", "platform_id": platform_id,
                      "success": True, "message": f"Bridge {host}:{port} 可达"}
        else:
            result = {"type": "ts", "platform_id": platform_id,
                      "success": False, "message": f"无法连接 Bridge {host}:{port} (errno={ret})"}
    except Exception as e:
        logger.warning(f"TS bridge test failed: {e}")
        result = {"type": "ts", "platform_id": platform_id,
                  "success": False, "message": f"测试失败: {str(e)[:300]}"}
    await _send(websocket, flow_id, "ack", "ack", {"ok": True, "test_result": result}, msg_id)
