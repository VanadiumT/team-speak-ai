"""
模型预热 — 应用启动时后台加载已配置的 AI 模型

仅预热初始化开销大的本地模型（OCR、STT），跳过轻量级 provider（TTS、LLM、VAD）。
配置不完整时输出 WARN 日志，说明缺少哪些字段。
"""

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.app_context import AppContext

logger = logging.getLogger(__name__)


def _find_default_preset(pm) -> tuple[str, str] | None:
    """从 preset manager 中找到默认 preset 的 (platform_id, model_id)"""
    data = pm.list_all()
    for p in data.get("platforms", []):
        models = p.get("models", [])
        if not models:
            continue
        default = next((m for m in models if m.get("is_default")), models[0])
        if default:
            return p["id"], default["id"]
    return None


def _validate_ocr_config(config: dict) -> list[str]:
    """校验 OCR 配置完整性，返回缺失字段列表"""
    missing = []
    provider = config.get("provider", "")
    if not provider:
        missing.append("provider")
    elif provider == "paddleocr":
        if not config.get("det_model_dir"):
            missing.append("det_model_dir")
        if not config.get("rec_model_dir"):
            missing.append("rec_model_dir")
    return missing


def _validate_stt_config(config: dict) -> list[str]:
    """校验 STT 配置完整性，返回缺失字段列表"""
    missing = []
    provider = config.get("provider", "")
    if not provider:
        missing.append("provider")
    elif provider == "sensevoice":
        if not config.get("model_dir"):
            missing.append("model_dir")
    elif provider == "whisper":
        if not config.get("model_name"):
            missing.append("model_name")
    elif provider == "minimax":
        if not config.get("api_key"):
            missing.append("api_key")
    return missing


def _preheat_ocr(config: dict) -> None:
    """同步加载 OCR 模型（在线程池中调用）"""
    from core.nodes.ocr_node import _load_ocr
    provider = config.get("provider", "easyocr")
    ocr_config = {}
    if provider == "easyocr":
        ocr_config = {
            "lang_list": config.get("lang_list", ["ch_sim", "en"]),
            "gpu": config.get("gpu", False),
        }
    elif provider == "paddleocr":
        ocr_config = {
            "det_model_dir": config.get("det_model_dir", "ch"),
            "rec_model_dir": config.get("rec_model_dir", "ch"),
            "use_angle_cls": config.get("use_angle_cls", True),
            "use_gpu": config.get("gpu", False),
            "lang": config.get("lang", "ch"),
        }
    _load_ocr(provider, ocr_config)


def _preheat_stt(config: dict) -> None:
    """同步加载 STT 模型（在线程池中调用）"""
    from core.nodes.stt_listen_node import _load_stt
    _load_stt(config)


async def preheat_models(ctx: "AppContext") -> None:
    """预热入口 — 由 AppContext.start_background_tasks() 调用"""
    preheat_cfg = ctx.preheat_manager.get_config()

    if not preheat_cfg.enabled:
        logger.info("[预热] 全局开关已关闭，跳过所有模型预热")
        return

    loop = asyncio.get_running_loop()
    warmed = []

    # ── OCR 预热 ──
    if preheat_cfg.ocr.enabled:
        preset = _find_default_preset(ctx.ocr_preset_manager)
        if preset:
            platform_id, model_id = preset
            try:
                config = ctx.ocr_preset_manager.get_effective_config(platform_id, model_id)
                missing = _validate_ocr_config(config)
                if missing:
                    logger.warning(f"[预热] OCR 配置不完整，跳过预热: 缺少 {', '.join(missing)}")
                else:
                    await loop.run_in_executor(None, _preheat_ocr, config)
                    warmed.append(f"OCR({config.get('provider', 'easyocr')})")
                    logger.info(f"[预热] OCR 加载完成: {config.get('provider', 'easyocr')}")
            except Exception as e:
                logger.warning(f"[预热] OCR 预热失败: {e}")
        else:
            logger.warning("[预热] OCR 无可用预设，跳过预热")

    # ── STT 预热 ──
    if preheat_cfg.stt.enabled:
        preset = _find_default_preset(ctx.stt_preset_manager)
        if preset:
            platform_id, model_id = preset
            try:
                config = ctx.stt_preset_manager.get_effective_config(platform_id, model_id)
                missing = _validate_stt_config(config)
                if missing:
                    logger.warning(f"[预热] STT 配置不完整，跳过预热: 缺少 {', '.join(missing)}")
                else:
                    await loop.run_in_executor(None, _preheat_stt, config)
                    warmed.append(f"STT({config.get('provider', 'sensevoice')})")
                    logger.info(f"[预热] STT 加载完成: {config.get('provider', 'sensevoice')}")
            except Exception as e:
                logger.warning(f"[预热] STT 预热失败: {e}")
        else:
            logger.warning("[预热] STT 无可用预设，跳过预热")

    if warmed:
        logger.info(f"[预热] 全部完成: {', '.join(warmed)}")
    else:
        logger.info("[预热] 无模型需要预热")
