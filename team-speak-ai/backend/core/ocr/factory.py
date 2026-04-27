from enum import Enum
from core.ocr.base import BaseOCR
from core.ocr.easyocr_ocr import EasyOCROCR
from core.ocr.paddleocr_ocr import PaddleOCROCR


class OCRProvider(Enum):
    EASYOCR = "easyocr"
    PADDLEOCR = "paddleocr"


def create_ocr(provider: OCRProvider, config: dict) -> BaseOCR:
    if provider == OCRProvider.EASYOCR:
        return EasyOCROCR(**config)
    elif provider == OCRProvider.PADDLEOCR:
        return PaddleOCROCR(**config)
    raise ValueError(f"Unknown OCR provider: {provider}")
