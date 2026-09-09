"""
Unit Tests for Geometric Symbol Detector (Door Swings)
"""

import pytest
from core.geometry.primitives import Point2D, Segment2D, Arc2D
from vision.detection.symbol_detector import GeometricSymbolDetector

def test_detect_door_swing():
    # 900mm door: hinge at (1000, 1000)
    hinge = Point2D(1000, 1000)
    # Leaf segment from hinge along X
    leaf = Segment2D(start=hinge, end=Point2D(1900, 1000), handle="L-DOOR-1")
    # Quarter-circle arc from 0° to 90° with radius 900
    arc = Arc2D(center=hinge, radius=900.0, start_angle_deg=0.0, end_angle_deg=90.0, handle="A-DOOR-1")

    detector = GeometricSymbolDetector()
    doors = detector.detect_doors_from_geometry([leaf], [arc])

    assert len(doors) == 1
    d = doors[0]
    assert d.width_mm == 900.0
    assert d.width_m == 0.90
    assert d.hinge == hinge
    assert d.confidence >= 0.95

def test_reject_full_circle_or_wrong_radius():
    hinge = Point2D(0, 0)
    leaf = Segment2D(start=hinge, end=Point2D(500, 0))
    # Radius 200mm is too small for an architectural door
    small_arc = Arc2D(center=hinge, radius=200.0, start_angle_deg=0.0, end_angle_deg=90.0)

    detector = GeometricSymbolDetector()
    doors = detector.detect_doors_from_geometry([leaf], [small_arc])
    assert len(doors) == 0
