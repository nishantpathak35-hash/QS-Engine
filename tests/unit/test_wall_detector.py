"""
Unit Tests for Wall Pairing & Centerline Solver
"""

import pytest
from core.geometry.primitives import Point2D, Segment2D
from semantics.walls.wall_detector import WallDetector, WallDetectionConfig

def test_wall_pairing_parallel_segments():
    # 2 parallel horizontal segments representing a 150mm thick wall, 5000mm long
    s1 = Segment2D(start=Point2D(0, 0), end=Point2D(5000, 0))
    s2 = Segment2D(start=Point2D(0, 150), end=Point2D(5000, 150))

    detector = WallDetector()
    walls = detector.detect_walls([s1, s2])

    assert len(walls) == 1
    w = walls[0]
    assert w.thickness_mm == 150.0
    # Centerline should be at y = 75
    assert pytest.approx(w.start.y) == 75.0
    assert pytest.approx(w.end.y) == 75.0
    assert pytest.approx(w.length_m) == 5.0

def test_wall_pairing_ignores_non_wall_spacing():
    # 2 parallel segments separated by 2000mm (a room width, not a wall thickness)
    s1 = Segment2D(start=Point2D(0, 0), end=Point2D(5000, 0))
    s2 = Segment2D(start=Point2D(0, 2000), end=Point2D(5000, 2000))

    detector = WallDetector()
    walls = detector.detect_walls([s1, s2])
    assert len(walls) == 0
