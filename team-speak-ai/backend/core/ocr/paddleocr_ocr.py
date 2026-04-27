import numpy as np
from core.ocr.base import BaseOCR, OcrResult


class PaddleOCROCR(BaseOCR):
    def __init__(self, det_model_dir="ch", rec_model_dir="ch",
                 use_angle_cls=True, use_gpu=False, lang="ch"):
        from paddleocr import PaddleOCR
        self.engine = PaddleOCR(
            det_model_dir=det_model_dir,
            rec_model_dir=rec_model_dir,
            use_angle_cls=use_angle_cls,
            use_gpu=use_gpu,
            lang=lang,
        )

    def recognize(self, image: np.ndarray) -> OcrResult:
        results = self.engine.ocr(image, cls=True)
        if results and results[0]:
            lines = [item[1][0] for item in results[0] if item[1][1] > 0.3]
        else:
            lines = []
        text = "\n".join(lines) if lines else "（未识别到文字）"
        return OcrResult(text=text, lines=lines, provider="paddleocr")
