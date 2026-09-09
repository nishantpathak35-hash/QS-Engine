"""
Unit Tests for Canonical Unit Normalization & Precision
"""

import pytest
from core.units import UnitsEngine, DisplayUnit, UnitCategory

def test_mm_to_m_conversion():
    assert UnitsEngine.mm_to_m(1000.0) == 1.0
    assert UnitsEngine.mm_to_m(4500.0) == 4.5
    assert UnitsEngine.mm_to_m(0.0) == 0.0

def test_mm2_to_sqm_conversion():
    # 1 sqm = 1,000,000 mm²
    assert UnitsEngine.mm2_to_sqm(1_000_000.0) == 1.0
    # 41.718394 sqm in mm²
    mm2 = 41_718_394.0
    assert UnitsEngine.mm2_to_sqm(mm2) == pytest.approx(41.718394)

def test_sqm_to_sqft_conversion():
    # 1 sqm ≈ 10.7639 sqft
    sqft = UnitsEngine.sqm_to_sqft(10.0)
    assert round(sqft, 2) == 107.64

def test_format_area_preserves_raw():
    formatted = UnitsEngine.format_area_sqm(41_718_394.0, decimals=2)
    assert formatted.raw_value == pytest.approx(41.718394)
    assert formatted.display_value == 41.72
    assert formatted.unit == DisplayUnit.SQM
    assert formatted.category == UnitCategory.AREA
    assert str(formatted) == "41.72 sqm"

def test_format_count():
    formatted = UnitsEngine.format_count(15)
    assert formatted.display_value == 15.0
    assert str(formatted) == "15 nos"
