"""
OCR 节点 — 图片文字识别

接收 input_image 节点的输出，对图片进行 OCR 识别。
使用 EasyOCR 引擎，支持中英文混合识别。
"""

import base64
import logging
import io
from PIL import Image
from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry

logger = logging.getLogger(__name__)


@NodeRegistry.register("ocr")
class OCRNode(BaseNode):
    """图片文字识别节点"""

    node_type = "ocr"
    _reader = None

    @classmethod
    def _get_reader(cls):
        if cls._reader is None:
            import easyocr
            cls._reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
        return cls._reader

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        file_input = context.inputs.get("file", "")
        filename = context.inputs.get("filename", "unknown.png")

        # Resolve base64 data: file_input may be a dict or a raw string
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

        await emit.emit_node_update(context.node_id, "processing", "正在识别图片文字...")

        # Decode base64 → PIL Image → OCR
        try:
            img_bytes = base64.b64decode(b64)
            img = Image.open(io.BytesIO(img_bytes))
            img = img.convert("RGB")
        except Exception as e:
            logger.exception("Failed to decode image")
            await emit.emit_node_update(context.node_id, "error", f"图片解码失败: {e}")
            return NodeOutput({"text": "", "error": str(e)})

        try:
            import numpy as np
            reader = self._get_reader()
            img_array = np.array(img)
            results = reader.readtext(img_array)
            lines = [item[1] for item in results if item[2] > 0.3]
            text = "\n".join(lines) if lines else "（未识别到文字）"
        except Exception as e:
            logger.exception("OCR recognition failed")
            await emit.emit_node_update(context.node_id, "error", f"OCR 识别失败: {e}")
            return NodeOutput({"text": "", "error": str(e)})

        logger.info(f"OCR result from {filename}: {len(text)} chars, {len(lines)} lines")

        await emit.emit_node_update(
            context.node_id,
            "completed",
            f"识别到 {len(lines)} 行文字",
            data={"text": text, "line_count": len(lines)},
        )

        return NodeOutput({"text": text, "line_count": len(lines)})
