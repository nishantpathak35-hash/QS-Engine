"""
Unit Tests for Text Context & Dimension Classifier
"""

import pytest
from vision.ocr.provider import OCRResult
from vision.ocr.text_classifier import TextContextClassifier, TextCategory

def test_classify_room_name():
    ocr_item = OCRResult(text="CONFERENCE ROOM 02", bbox=(10, 20, 100, 20), confidence=0.95)
    classified = TextContextClassifier.classify(ocr_item)
    assert classified.category == TextCategory.ROOM_NAME
    assert classified.parsed_value == "CONFERENCE ROOM 02"

def test_classify_linear_dimension():
    # 3000 mm
    ocr_item1 = OCRResult(text="3000", bbox=(50, 50, 40, 15), confidence=0.92)
    c1 = TextContextClassifier.classify(ocr_item1)
    assert c1.category == TextCategory.DIMENSION
    assert c1.parsed_value == 3000.0

    # 4.50 m -> 4500 mm
    ocr_item2 = OCRResult(text="4.50 m", bbox=(50, 50, 50, 15), confidence=0.90)
    c2 = TextContextClassifier.classify(ocr_item2)
    assert c2.category == TextCategory.DIMENSION
    assert c2.parsed_value == 4500.0

def test_classify_opening_tag():
    ocr_d1 = OCRResult(text="D1", bbox=(0, 0, 20, 20), confidence=0.98)
    c_d1 = TextContextClassifier.classify(ocr_d1)
    assert c_d1.category == TextCategory.OPENING_TAG
    assert c_d1.parsed_value == "D1"

    ocr_w2 = OCRResult(text="W-02", bbox=(0, 0, 20, 20), confidence=0.95)
    c_w2 = TextContextClassifier.classify(ocr_w2)
    assert c_w2.category == TextCategory.OPENING_TAG
    assert c_w2.parsed_value == "W-02"

def test_classify_finish_code():
    ocr_f01 = OCRResult(text="F-01", bbox=(0, 0, 20, 20), confidence=0.96)
    c_f = TextContextClassifier.classify(ocr_f01)
    assert c_f.category == TextCategory.FINISH_CODE
    assert c_f.parsed_value == "F-01"
