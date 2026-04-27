from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np


@dataclass
class OcrResult:
    text: str
    lines: list[str]
    provider: str


class BaseOCR(ABC):
    @abstractmethod
    def recognize(self, image: np.ndarray) -> OcrResult:
        """对图片数组进行文字识别"""
