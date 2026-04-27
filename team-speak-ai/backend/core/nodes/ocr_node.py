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
from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry
from config import settings

logger = logging.getLogger(__name__)


def _load_easyocr():
    import easyocr
    return easyocr.Reader(['ch_sim', 'en'], gpu=False)


def _load_paddleocr():
    from paddleocr import PaddleOCR
    return PaddleOCR(
        det_model_dir=settings.paddleocr_det_model,
        rec_model_dir=settings.paddleocr_rec_model,
        use_angle_cls=settings.paddleocr_use_angle_cls,
        use_gpu=settings.paddleocr_use_gpu,
        lang='ch',
    )


_easyocr_reader = None
_paddleocr_engine = None


def _get_ocr():
    global _easyocr_reader, _paddleocr_engine
    provider = settings.ocr_provider

    if provider == "paddleocr":
        if _paddleocr_engine is None:
            _paddleocr_engine = _load_paddleocr()
        return ("paddleocr", _paddleocr_engine)
    else:
        if _easyocr_reader is None:
            _easyocr_reader = _load_easyocr()
        return ("easyocr", _easyocr_reader)


def _run_ocr(img_array):
    import numpy as np

    provider, engine = _get_ocr()

    if provider == "paddleocr":
        results = engine.ocr(img_array, cls=True)
        if results and results[0]:
            lines = [item[1][0] for item in results[0] if item[1][1] > 0.3]
        else:
            lines = []
    else:
        results = engine.readtext(img_array)
        lines = [item[1] for item in results if item[2] > 0.3]

    text = "\n".join(lines) if lines else "（未识别到文字）"
    return text, lines, provider


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

        provider = settings.ocr_provider
        await emit.emit_node_update(context.node_id, "processing", f"正在使用 {provider} 识别图片文字...")

        try:
            img_bytes = base64.b64decode(b64)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        except Exception as e:
            logger.exception("Failed to decode image")
            await emit.emit_node_update(context.node_id, "error", f"图片解码失败: {e}")
            return NodeOutput({"text": "", "error": str(e)})

        try:
            import numpy as np
            img_array = np.array(img)
            text, lines, used_provider = _run_ocr(img_array)
        except Exception as e:
            logger.exception("OCR recognition failed")
            await emit.emit_node_update(context.node_id, "error", f"OCR 识别失败: {e}")
            return NodeOutput({"text": "", "error": str(e)})

        logger.info(f"OCR result [{used_provider}] from {filename}: {len(text)} chars, {len(lines)} lines")

        await emit.emit_node_update(
            context.node_id,
            "completed",
            f"[{used_provider}] 识别到 {len(lines)} 行文字",
            data={"text": text, "line_count": len(lines), "provider": used_provider},
        )

        return NodeOutput({"text": text, "line_count": len(lines), "provider": used_provider})
