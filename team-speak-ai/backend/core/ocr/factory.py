import logging
from enum import Enum
from core.ocr.base import BaseOCR
from core.ocr.easyocr_ocr import EasyOCROCR

logger = logging.getLogger(__name__)

# paddleocr 是可选依赖，未安装时回退到 easyocr
try:
    from core.ocr.paddleocr_ocr import PaddleOCROCR
    _HAS_PADDLEOCR = True
except ImportError:
    _HAS_PADDLEOCR = False
    PaddleOCROCR = None
    logger.info("paddleocr not installed, will fall back to easyocr")


class OCRProvider(Enum):
    EASYOCR = "easyocr"
    PADDLEOCR = "paddleocr"


def create_ocr(provider: OCRProvider, config: dict) -> BaseOCR:
    if provider == OCRProvider.EASYOCR:
        return EasyOCROCR(**config)
    elif provider == OCRProvider.PADDLEOCR:
        if not _HAS_PADDLEOCR:
            logger.warning("paddleocr not installed, falling back to easyocr")
            return EasyOCROCR(**config)
        return PaddleOCROCR(**config)
    raise ValueError(f"Unknown OCR provider: {provider}")
