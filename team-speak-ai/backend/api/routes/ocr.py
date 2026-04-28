"""
OCR REST API — 多方案 OCR 识别端点

支持 PaddleOCR 和 EasyOCR 两种引擎，通过 config.settings.ocr_provider 切换。
"""

import io
import json
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from PIL import Image
import numpy as np

from config import settings
from services.file_storage import file_storage
from core.ocr.factory import create_ocr, OCRProvider
from core.ocr.base import OcrResult

logger = logging.getLogger(__name__)
router = APIRouter()

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


def _run_ocr(img_bytes: bytes) -> OcrResult:
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img_array = np.array(img)
    return _get_ocr().recognize(img_array)


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

    logger.info("=" * 50)
    logger.info(f"OCR API 识别结果 [{result.provider}]")
    logger.info(f"行数: {len(result.lines)} | 总字符: {len(result.text)}")
    logger.info(f"识别文字:\n{result.text}")
    logger.info("=" * 50)

    return {
        "success": True,
        "data": {
            "text": result.text,
            "line_count": len(result.lines),
            "lines": result.lines,
            "provider": result.provider,
        },
    }


@router.get("/providers")
async def list_providers():
    """列出可用的 OCR 方案"""
    return {
        "current": settings.ocr_provider,
        "available": ["easyocr", "paddleocr"],
    }
