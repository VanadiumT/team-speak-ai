"""
OCR REST API — 多方案 OCR 识别端点

支持 PaddleOCR 和 EasyOCR 两种引擎，通过 config.settings.ocr_provider 切换。
"""

import base64
import io
import json
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional

from config import settings
from services.file_storage import file_storage

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_easyocr_reader():
    """延迟加载 EasyOCR"""
    import easyocr
    return easyocr.Reader(['ch_sim', 'en'], gpu=False)


def _get_paddleocr_engine():
    """延迟加载 PaddleOCR"""
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
    """根据配置获取 OCR 引擎"""
    global _easyocr_reader, _paddleocr_engine
    provider = settings.ocr_provider

    if provider == "paddleocr":
        if _paddleocr_engine is None:
            _paddleocr_engine = _get_paddleocr_engine()
        return ("paddleocr", _paddleocr_engine)
    else:
        if _easyocr_reader is None:
            _easyocr_reader = _get_easyocr_reader()
        return ("easyocr", _easyocr_reader)


def _run_ocr(img_bytes: bytes):
    """执行 OCR 识别"""
    from PIL import Image
    import numpy as np

    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img_array = np.array(img)

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
    return {
        "text": text,
        "line_count": len(lines),
        "lines": lines,
        "provider": provider,
    }


@router.post("/recognize")
async def recognize_image(
    file: Optional[UploadFile] = File(None),
    file_id: Optional[str] = Form(None),
    include_boxes: bool = Form(False),
):
    """
    图片 OCR 识别

    支持两种输入方式:
    - file: 直接上传图片文件
    - file_id: 使用已上传文件的 ID
    """
    if file:
        content = await file.read()
    elif file_id:
        file_info = await file_storage.get(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")
        content = await file_storage.get_content(file_id)
    else:
        raise HTTPException(status_code=400, detail="需要提供 file 或 file_id")

    try:
        result = _run_ocr(content)
    except Exception as e:
        logger.exception("OCR 识别失败")
        raise HTTPException(status_code=500, detail=f"OCR 识别失败: {e}")

    return {"success": True, "data": result}


@router.get("/providers")
async def list_providers():
    """列出可用的 OCR 方案"""
    return {
        "current": settings.ocr_provider,
        "available": ["easyocr", "paddleocr"],
    }
