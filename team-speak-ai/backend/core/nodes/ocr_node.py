"""
OCR 节点 — 图片文字识别，支持预设系统

接收 input_image 节点的输出，对图片进行 OCR 识别。
通过预设系统 (OcrPresetManager) 切换引擎:
- easyocr: 离线中英文识别
- paddleocr: 百度 PaddleOCR，中文更优

CPU 密集型操作（模型加载、推理）通过线程池执行，避免阻塞事件循环。
"""

import asyncio
import base64
import logging
import io
from PIL import Image
import numpy as np

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput, NodeState
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry
from core.ocr.factory import create_ocr, OCRProvider
from core.app_context import get_app_context
from config import settings

logger = logging.getLogger(__name__)

_ocr_cache: dict[str, object] = {}  # config_key → OCR instance（支持多配置并发）


def _ocr_config_hash(provider, config):
    return f"{provider}:{sorted(config.items())}"


def _load_ocr(provider, config):
    """在调用线程中加载 OCR 模型（供 run_in_executor 使用）。按配置哈希缓存，不同配置互不干扰。"""
    key = _ocr_config_hash(provider, config)
    if key not in _ocr_cache:
        _ocr_cache[key] = create_ocr(OCRProvider(provider), config)
    return _ocr_cache[key]


def _run_ocr(img_array, provider, config):
    """在调用线程中执行 OCR 识别（供 run_in_executor 使用）"""
    ocr = _load_ocr(provider, config)
    return ocr.recognize(img_array)


@NodeRegistry.register("ocr")
class OCRNode(BaseNode):
    """图片文字识别节点 — 多方案 OCR，支持预设配置"""

    node_type = "ocr"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        self.node_id = context.node_id
        cfg = context.node_config

        # ── 解析配置 ──
        try:
            if cfg.get("platform_id") and cfg.get("model_id"):
                effective = self._resolve_preset_config(cfg)
            else:
                effective = self._resolve_legacy_config(cfg)
        except Exception as e:
            self._log_warning(f"OCR config resolution failed: {e}, falling back to legacy")
            effective = self._resolve_legacy_config(cfg)

        provider = effective["provider"]
        ocr_config = effective["ocr_config"]
        label = effective.get("label", provider)

        # ── 获取输入图片 ──
        file_input = context.inputs.get("ocr", "")
        filename = context.inputs.get("filename", "unknown.png")

        if isinstance(file_input, dict):
            b64 = file_input.get("data", "") or file_input.get("file", "")
            filename = file_input.get("filename", filename)
        elif isinstance(file_input, str):
            b64 = file_input
        else:
            self._log_error("未收到图片数据")
            await emit.emit_node_update(context.node_id, NodeState.ERROR, "未收到图片数据")
            return NodeOutput({"text": "", "error": "no_image_data"})

        if not b64:
            self._log_error("图片数据为空")
            await emit.emit_node_update(context.node_id, NodeState.ERROR, "图片数据为空")
            return NodeOutput({"text": "", "error": "empty_image_data"})

        self._log_info(f"[{label}] 识别图片文字...")
        await emit.emit_node_update(
            context.node_id, "processing",
            f"[{label}] 识别图片文字...",
        )

        try:
            img_bytes = base64.b64decode(b64)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        except Exception as e:
            self._log_exception("Failed to decode image")
            raise self._wrap_error("图片解码失败", e) from e

        try:
            img_array = np.array(img)
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, _run_ocr, img_array, provider, ocr_config)
        except Exception as e:
            self._log_exception("OCR recognition failed")
            raise self._wrap_error("OCR 识别失败", e) from e

        self._log_info(f"[{result.provider}] 识别到 {len(result.lines)} 行，{len(result.text)} 字符")
        await emit.emit_node_log_entry(
            context.node_id, "success",
            f"[{result.provider}] 识别到 {len(result.lines)} 行，{len(result.text)} 字符",
        )
        await emit.emit_node_log_entry(
            context.node_id, "info",
            f"识别文字:\n{result.text}",
        )

        await emit.emit_node_update(
            context.node_id,
            "completed",
            f"[{result.provider}] 识别到 {len(result.lines)} 行文字",
            data={"text": result.text, "line_count": len(result.lines), "provider": result.provider},
        )

        return NodeOutput({
            "text": result.text,
            "line_count": len(result.lines),
            "provider": result.provider,
        })

    # ═══════════════════════════════════════════════════════
    # Internal helpers
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def _resolve_preset_config(cfg: dict) -> dict:
        """从 OCR 预设解析配置"""
        pm = get_app_context().ocr_preset_manager
        effective = BaseNode._resolve_preset_with_fallback(cfg, pm, legacy_fn=OCRNode._resolve_legacy_config)
        provider = effective.pop("provider", "easyocr")
        label = effective.pop("label", provider)
        ocr_config = OCRNode._build_ocr_config(provider, effective)
        logger.info(f"OCR effective config: provider={provider}, gpu={ocr_config.get('gpu', ocr_config.get('use_gpu'))}")
        return {"provider": provider, "ocr_config": ocr_config, "label": label}

    @staticmethod
    def _resolve_legacy_config(cfg: dict) -> dict:
        """旧格式兼容：无预设时使用 .env 配置"""
        provider = cfg.get("engine", settings.ocr_provider)
        ocr_config = OCRNode._build_ocr_config(provider, {
            "lang_list": cfg.get("lang_list") or cfg.get("language") or ["ch_sim", "en"],
            "lang": cfg.get("lang", "ch"),
            "gpu": cfg.get("gpu", False),
            "use_angle_cls": cfg.get("use_angle_cls", settings.paddleocr_use_angle_cls),
            "confidence_threshold": cfg.get("confidence_threshold", 0.3),
            "det_model_dir": settings.paddleocr_det_model,
            "rec_model_dir": settings.paddleocr_rec_model,
        })
        return {"provider": provider, "ocr_config": ocr_config}

    @staticmethod
    def _build_ocr_config(provider: str, effective: dict) -> dict:
        """将 effective config 转换为对应 OCR 引擎的构造参数"""
        if provider == "easyocr":
            return {
                "lang_list": effective.get("lang_list", ["ch_sim", "en"]),
                "gpu": effective.get("gpu", False),
            }
        elif provider == "paddleocr":
            return {
                "det_model_dir": effective.get("det_model_dir") or settings.paddleocr_det_model,
                "rec_model_dir": effective.get("rec_model_dir") or settings.paddleocr_rec_model,
                "use_angle_cls": effective.get("use_angle_cls", True),
                "use_gpu": effective.get("gpu", False),
                "lang": effective.get("lang", "ch"),
            }
        return effective
