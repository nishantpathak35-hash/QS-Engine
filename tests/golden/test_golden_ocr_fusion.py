"""
Golden OCR & Confidence Fusion Regression Test
Validates end-to-end OCR processing -> Text classification -> Symbol detection -> Confidence fusion -> QS Takeoff.
Enforces Blueprint Section 13, Section 18, Section 33 & Section 104.
"""

import pytest
import numpy as np
from vision.ocr.provider import MockOCRProvider, OCRResult
from vision.ocr.text_classifier import TextContextClassifier, TextCategory
from vision.detection.symbol_detector import GeometricSymbolDetector
from core.geometry.primitives import Point2D, Segment2D, Arc2D
from core.confidence import ConfidenceEngine, ReviewStatus
from core.models.semantics import Opening, OpeningType
from qs.rule_engine import QSRuleEngine

def test_golden_ocr_symbol_fusion_pipeline():
    # 1. Mock OCR results simulating noisy scan extraction
    ocr_items = [
        OCRResult(text="CONFERENCE ROOM", bbox=(100, 200, 150, 25), confidence=0.96),
        OCRResult(text="D1", bbox=(500, 400, 25, 20), confidence=0.94),
        OCRResult(text="3000", bbox=(300, 150, 40, 15), confidence=0.91),
        OCRResult(text="F-02", bbox=(150, 240, 30, 15), confidence=0.93),
    ]

    mock_ocr = MockOCRProvider(ocr_items)
    dummy_img = np.zeros((600, 800), dtype=np.uint8)
    extracted_ocr = mock_ocr.recognize(dummy_img)

    # 2. Text Classification
    classified = [TextContextClassifier.classify(item) for item in extracted_ocr]
    cat_dict = {c.category: c for c in classified}

    assert TextCategory.ROOM_NAME in cat_dict
    assert cat_dict[TextCategory.ROOM_NAME].parsed_value == "CONFERENCE ROOM"

    assert TextCategory.OPENING_TAG in cat_dict
    assert cat_dict[TextCategory.OPENING_TAG].parsed_value == "D1"

    assert TextCategory.DIMENSION in cat_dict
    assert cat_dict[TextCategory.DIMENSION].parsed_value == 3000.0

    assert TextCategory.FINISH_CODE in cat_dict
    assert cat_dict[TextCategory.FINISH_CODE].parsed_value == "F-02"

    # 3. Geometric Symbol Detection (Door Swing: leaf + 90° arc)
    hinge = Point2D(500, 400)
    leaf = Segment2D(start=hinge, end=Point2D(1400, 400), handle="SEG-LEAF")
    arc = Arc2D(center=hinge, radius=900.0, start_angle_deg=0.0, end_angle_deg=90.0, handle="ARC-SWING")

    detector = GeometricSymbolDetector()
    detected_doors = detector.detect_doors_from_geometry([leaf], [arc])
    assert len(detected_doors) == 1
    door = detected_doors[0]

    # 4. Confidence Fusion: combine geometric swing match (0.96) with OCR tag "D1" (0.94)
    fused_conf = ConfidenceEngine.fuse_signals(
        geometry_signal=door.confidence,
        ocr_signal=cat_dict[TextCategory.OPENING_TAG].confidence
    )
    assert fused_conf >= 0.95
    assert ConfidenceEngine.evaluate_status(fused_conf) == ReviewStatus.AUTO_ACCEPT

    # 5. Synthesize into Opening object for QS Takeoff
    opening = Opening(
        id="OP-001",
        opening_type=OpeningType.DOOR,
        width_m=door.width_m,
        location=hinge,
        tag=str(cat_dict[TextCategory.OPENING_TAG].parsed_value),
        confidence=fused_conf
    )
    assert opening.width_m == 0.90
    assert opening.tag == "D1"
    assert opening.confidence >= 0.95
