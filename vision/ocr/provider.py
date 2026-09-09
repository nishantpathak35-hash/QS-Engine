"""
QS Quantification Engine — Provider-Agnostic OCR Engine Interface
Decouples the measurement engine from any single AI/OCR library.
Enforces Blueprint Section 13 & Section 106 (No Single Model Dependency).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class OCRResult:
    text: str
    bbox: tuple[float, float, float, float]  # (x, y, width, height) in image pixels/coords
    confidence: float
    rotation_deg: float = 0.0

    @property
    def center(self) -> tuple[float, float]:
        x, y, w, h = self.bbox
        return (x + w / 2.0, y + h / 2.0)


class BaseOCRProvider(ABC):
    """Abstract interface for local OCR engines (PaddleOCR, Tesseract, ONNX)."""

    @abstractmethod
    def recognize(self, image: np.ndarray) -> list[OCRResult]:
        """Runs optical character recognition on an input image array."""
        pass


class MockOCRProvider(BaseOCRProvider):
    """Deterministic mock provider for unit testing and CI benchmarks."""

    def __init__(self, predefined_results: list[OCRResult] | None = None):
        self.predefined_results = predefined_results or []

    def set_results(self, results: list[OCRResult]):
        self.predefined_results = results

    def recognize(self, image: np.ndarray) -> list[OCRResult]:
        return self.predefined_results


class PaddleOCRProvider(BaseOCRProvider):
    """Local PaddleOCR engine implementation with graceful fallback."""

    def __init__(self, lang: str = "en", use_gpu: bool = False):
        self.lang = lang
        self.use_gpu = use_gpu
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            try:
                from paddleocr import PaddleOCR
                self._engine = PaddleOCR(use_angle_cls=True, lang=self.lang, use_gpu=self.use_gpu)
            except ImportError:
                raise ImportError(
                    "PaddleOCR is not installed. To run real optical recognition, install: "
                    "pip install paddlepaddle paddleocr"
                )
        return self._engine

    def recognize(self, image: np.ndarray) -> list[OCRResult]:
        engine = self._get_engine()
        results = engine.ocr(image, cls=True)
        ocr_items: list[OCRResult] = []

        if not results or not results[0]:
            return []

        for line in results[0]:
            coords = line[0]  # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
            text, conf = line[1]
            xs = [p[0] for p in coords]
            ys = [p[1] for p in coords]
            bbox = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
            ocr_items.append(OCRResult(
                text=text.strip(),
                bbox=bbox,
                confidence=float(conf)
            ))

        return ocr_items
