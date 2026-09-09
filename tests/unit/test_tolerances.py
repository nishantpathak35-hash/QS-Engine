"""
Unit Tests for Tolerance Engine & Snapping Rules
"""

import pytest
from core.tolerances import ToleranceEvaluator, DEFAULT_TOLERANCES

def test_points_coincide_within_snap_tolerance():
    p1 = (100.0, 200.0)
    # Point within 2mm (< 3mm tolerance)
    p2 = (101.5, 200.5)
    assert ToleranceEvaluator.points_coincide(p1, p2, tolerance_mm=3.0) is True

    # Point outside 3mm tolerance (5mm away)
    p3 = (105.0, 200.0)
    assert ToleranceEvaluator.points_coincide(p1, p3, tolerance_mm=3.0) is False

def test_lines_parallel_check():
    # Exactly parallel (0° and 180°)
    assert ToleranceEvaluator.lines_parallel(0.0, 0.0) is True
    assert ToleranceEvaluator.lines_parallel(0.0, 180.0) is True
    assert ToleranceEvaluator.lines_parallel(90.0, 270.0) is True

    # Parallel within 0.8° tolerance
    assert ToleranceEvaluator.lines_parallel(45.0, 45.8, tolerance_deg=1.0) is True

    # Not parallel (5° divergence)
    assert ToleranceEvaluator.lines_parallel(0.0, 5.0, tolerance_deg=1.0) is False
