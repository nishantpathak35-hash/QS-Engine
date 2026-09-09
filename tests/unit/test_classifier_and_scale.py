"""
Unit Tests for Drawing Classifier & Scale Calibration Engine
"""

import pytest
from pathlib import Path
from parsers.classifier import DrawingTypeClassifier, DrawingType
from parsers.pdf_vector.scale_calibrator import ScaleCalibrator, CalibratedScale, PT_TO_PAPER_MM
from core.exceptions import ScaleRequiredError

def test_scale_regex_discovery():
    text = "PROJECT: LUXURY APARTMENTS\nDRAWING: A-102\nScale: 1:50\nDATE: 2026-09"
    cal = ScaleCalibrator.calibrate_from_text(text)
    assert cal is not None
    assert cal.ratio_string == "1:50"
    assert pytest.approx(cal.scale_factor_mm_per_pt) == PT_TO_PAPER_MM * 50.0

def test_scale_from_dimension():
    # 3000 mm measured over 85.04 points
    cal = ScaleCalibrator.calibrate_from_dimension(3000.0, 85.03937)
    assert pytest.approx(cal.scale_factor_mm_per_pt, abs=0.1) == 35.28
    assert cal.ratio_string == "1:100"

def test_scale_missing_raises_error():
    noisy_text = "GENERAL NOTES:\n1. ALL DIMENSIONS ARE IN MM.\n2. DO NOT SCALE DRAWING."
    with pytest.raises(ScaleRequiredError):
        ScaleCalibrator.calibrate_or_fail(noisy_text)

def test_scale_user_override():
    cal = ScaleCalibrator.calibrate_or_fail("No scale mentioned", user_scale_ratio=200)
    assert cal.ratio_string == "1:200"
    assert cal.source == "user_calibration"
