"""
OCR 节点 — 图片文字识别，支持多方案

接收 input_image 节点的输出，对图片进行 OCR 识别。
通过 config.settings.ocr_provider 切换引擎:
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
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry
from core.ocr.factory import create_ocr, OCRProvider
from config import settings

logger = logging.getLogger(__name__)

_ocr_instance = None


def _load_ocr():
    """在调用线程中加载 OCR 模型（供 run_in_executor 使用）"""
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


def _run_ocr(img_array):
    """在调用线程中执行 OCR 识别（供 run_in_executor 使用）"""
    ocr = _load_ocr()
    return ocr.recognize(img_array)


@NodeRegistry.register("ocr")
class OCRNode(BaseNode):
    """图片文字识别节点 — 多方案 OCR"""

    node_type = "ocr"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        file_input = context.inputs.get("ocr", "")
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
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, _run_ocr, img_array)
        except Exception as e:
            logger.exception("OCR recognition failed")
            await emit.emit_node_update(context.node_id, "error", f"OCR 识别失败: {e}")
            return NodeOutput({"text": "", "error": str(e)})

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
