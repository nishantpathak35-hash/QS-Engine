"""
QS Quantification Engine — Text Context & Dimension Classifier
Classifies raw OCR text strings into semantic categories (Room Names, Dimensions, Tags, Finishes).
Enforces Blueprint Section 13 (Module 7) & Section 14 (Module 8).
"""

from __future__ import annotations
import re
from enum import Enum
from dataclasses import dataclass
from vision.ocr.provider import OCRResult

class TextCategory(str, Enum):
    ROOM_NAME = "room_name"
    DIMENSION = "dimension"
    OPENING_TAG = "opening_tag"
    FINISH_CODE = "finish_code"
    SCALE_NOTE = "scale_note"
    GENERAL_NOTE = "general_note"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ClassifiedText:
    raw_text: str
    category: TextCategory
    parsed_value: str | float | None
    confidence: float
    bbox: tuple[float, float, float, float]


class TextContextClassifier:
    """Categorizes OCR text by spatial context, regex patterns, and architectural conventions."""

    # Architectural room patterns
    ROOM_PATTERNS = [
        re.compile(r".*\b(room|office|cabin|conference|board\s*room|lobby|toilet|washroom|pantry|kitchen|store|shaft|balcony|corridor|passage|reception|utility|consultation|ward|clinic|lab|lounge|hall|area|suite|booth|ot|pharmacy|testing|fitting|trial|counter|showroom|stockroom|bedroom|living)\b.*", re.IGNORECASE),
        re.compile(r"^[A-Z0-9\s\-_/]{3,40}$") # Uppercase titles like "MAIN ENTRANCE", "CONSULTATION 1", "ROOM 101"
    ]

    # Dimension patterns (e.g. 3000, 4500, 2.70m, 900)
    DIMENSION_PATTERNS = [
        (re.compile(r"^\b(\d{2,5})\b$"), lambda m: float(m.group(1))),
        (re.compile(r"^\b(\d+\.\d+)\s*m\b", re.IGNORECASE), lambda m: float(m.group(1)) * 1000.0),
        (re.compile(r"^\b(\d+)\s*mm\b", re.IGNORECASE), lambda m: float(m.group(1))),
    ]

    # Door / Window tags (e.g. D1, D-02, W-01, FD-1)
    TAG_PATTERNS = [
        re.compile(r"^(D|W|FD|GD|WIN|DR)[-_]?\d{1,3}[A-Z]?$", re.IGNORECASE),
    ]

    # Finish codes (e.g. F-01, F-02, CP-01, VT-02, P-01, SK-01)
    FINISH_PATTERNS = [
        re.compile(r"^(F|W|C|CP|VT|FL|CL|SK)[-_]?\d{1,3}$", re.IGNORECASE),
    ]

    @classmethod
    def classify_text(cls, text: str) -> tuple[TextCategory, str | float | None]:
        """Classifies a plain string without requiring bounding boxes."""
        dummy_ocr = OCRResult(text=text, confidence=1.0, bbox=(0, 0, 0, 0))
        classified = cls.classify(dummy_ocr)
        return classified.category, classified.parsed_value

    @classmethod
    def classify(cls, ocr_item: OCRResult) -> ClassifiedText:
        text = ocr_item.text.strip()

        # 1. Check Scale Note
        if re.search(r"scale\s*[:\-=]?\s*1\s*:\s*\d+", text, re.IGNORECASE):
            return ClassifiedText(
                raw_text=text,
                category=TextCategory.SCALE_NOTE,
                parsed_value=text,
                confidence=ocr_item.confidence,
                bbox=ocr_item.bbox
            )

        # 2. Check Opening Tag (D1, W1, etc.)
        for pattern in cls.TAG_PATTERNS:
            if pattern.match(text):
                return ClassifiedText(
                    raw_text=text,
                    category=TextCategory.OPENING_TAG,
                    parsed_value=text.upper(),
                    confidence=min(0.98, ocr_item.confidence * 1.05),
                    bbox=ocr_item.bbox
                )

        # 3. Check Finish Code (F-01, CP-01)
        for pattern in cls.FINISH_PATTERNS:
            if pattern.match(text):
                return ClassifiedText(
                    raw_text=text,
                    category=TextCategory.FINISH_CODE,
                    parsed_value=text.upper(),
                    confidence=min(0.95, ocr_item.confidence * 1.02),
                    bbox=ocr_item.bbox
                )

        # 4. Check Linear Dimension (3000, 2.7m)
        for pattern, extractor in cls.DIMENSION_PATTERNS:
            match = pattern.match(text)
            if match:
                val_mm = extractor(match)
                # Plausible architectural dimension: 50mm to 50,000mm
                if 50.0 <= val_mm <= 50_000.0:
                    return ClassifiedText(
                        raw_text=text,
                        category=TextCategory.DIMENSION,
                        parsed_value=val_mm,
                        confidence=ocr_item.confidence,
                        bbox=ocr_item.bbox
                    )

        # 5. Check Room Name
        for pattern in cls.ROOM_PATTERNS:
            if pattern.match(text) and len(text) >= 3 and not text.isdigit():
                return ClassifiedText(
                    raw_text=text,
                    category=TextCategory.ROOM_NAME,
                    parsed_value=text.upper(),
                    confidence=ocr_item.confidence,
                    bbox=ocr_item.bbox
                )

        # 6. LLM Fallback for ambiguous text annotations (Blueprint Section 54/55)
        try:
            from core.ai.factory import LLMProviderFactory
            provider = LLMProviderFactory.get_provider()
            ai_res = provider.classify_annotation(text)
            if ai_res.confidence >= 0.70 and ai_res.semantic_type == "room_name":
                return ClassifiedText(
                    raw_text=text,
                    category=TextCategory.ROOM_NAME,
                    parsed_value=(ai_res.normalized_value or text).upper(),
                    confidence=ai_res.confidence,
                    bbox=ocr_item.bbox
                )
        except Exception:
            pass

        return ClassifiedText(
            raw_text=text,
            category=TextCategory.UNKNOWN,
            parsed_value=None,
            confidence=ocr_item.confidence * 0.7,
            bbox=ocr_item.bbox
        )
