import numpy as np
from core.ocr.base import BaseOCR, OcrResult


class EasyOCROCR(BaseOCR):
    def __init__(self, lang_list: list = None, gpu: bool = False):
        import easyocr
        self.reader = easyocr.Reader(lang_list or ['ch_sim', 'en'], gpu=gpu)

    def recognize(self, image: np.ndarray) -> OcrResult:
        results = self.reader.readtext(image)
        lines = [item[1] for item in results if item[2] > 0.3]
        text = "\n".join(lines) if lines else "（未识别到文字）"
        return OcrResult(text=text, lines=lines, provider="easyocr")
