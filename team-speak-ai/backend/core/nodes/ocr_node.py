"""
OCR 节点 — 图片文字识别，支持多方案

接收 input_image 节点的输出，对图片进行 OCR 识别。
通过 config.settings.ocr_provider 切换引擎:
- easyocr: 离线中英文识别
- paddleocr: 百度 PaddleOCR，中文更优
"""

import base64
import logging
import io
from PIL import Image
import numpy as np

from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry
from core.ocr.factory import create_ocr, OCRProvider
from config import settings

logger = logging.getLogger(__name__)

_ocr_instance = None


def _get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        provider = OCRProvider(settings.ocr_provider)
        config = {
            "easyocr": {"lang_list": ['ch_sim', 'en'], "gpu": False},
            "paddleocr": {
                "det_model_dir": settings.paddleocr_det_model,
                "rec_model_dir": settings.paddleocr_rec_model,
                "use_angle_cls": settings.paddleocr_use_angle_cls,
                "use_gpu": settings.paddleocr_use_gpu,
            },
        }
        _ocr_instance = create_ocr(provider, config.get(settings.ocr_provider, {}))
    return _ocr_instance


@NodeRegistry.register("ocr")
class OCRNode(BaseNode):
    """图片文字识别节点 — 多方案 OCR"""

    node_type = "ocr"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        file_input = context.inputs.get("file", "")
        filename = context.inputs.get("filename", "unknown.png")

        if isinstance(file_input, dict):
            b64 = file_input.get("data", "") or file_input.get("file", "")
            filename = file_input.get("filename", filename)
        elif isinstance(file_input, str):
            b64 = file_input
        else:
            await emit.emit_node_update(context.node_id, "error", "未收到图片数据")
            return NodeOutput({"text": "", "error": "no_image_data"})

        if not b64:
            await emit.emit_node_update(context.node_id, "error", "图片数据为空")
            return NodeOutput({"text": "", "error": "empty_image_data"})

        provider_name = settings.ocr_provider
        await emit.emit_node_update(
            context.node_id, "processing",
            f"正在使用 {provider_name} 识别图片文字...",
        )

        try:
            img_bytes = base64.b64decode(b64)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        except Exception as e:
            logger.exception("Failed to decode image")
            await emit.emit_node_update(context.node_id, "error", f"图片解码失败: {e}")
            return NodeOutput({"text": "", "error": str(e)})

        try:
            img_array = np.array(img)
            ocr = _get_ocr()
            result = ocr.recognize(img_array)
        except Exception as e:
            logger.exception("OCR recognition failed")
            await emit.emit_node_update(context.node_id, "error", f"OCR 识别失败: {e}")
            return NodeOutput({"text": "", "error": str(e)})

        logger.info("=" * 50)
        logger.info(f"OCR 识别结果 [{result.provider}] | 文件: {filename}")
        logger.info(f"行数: {len(result.lines)} | 总字符: {len(result.text)}")
        logger.info(f"识别文字:\n{result.text}")
        logger.info("=" * 50)

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
