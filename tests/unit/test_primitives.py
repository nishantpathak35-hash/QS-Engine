"""
Unit Tests for Core 2D Geometric Primitives & Shoelace Math
"""

import pytest
from core.geometry.primitives import Point2D, Segment2D, Polygon2D

def test_point_distance():
    p1 = Point2D(0.0, 0.0)
    p2 = Point2D(3000.0, 4000.0)
    assert p1.distance_to(p2) == 5000.0

def test_segment_properties():
    p1 = Point2D(1000.0, 1000.0)
    p2 = Point2D(5000.0, 1000.0)
    seg = Segment2D(start=p1, end=p2, layer="A-WALL")
    assert seg.length_mm == 4000.0
    assert seg.angle_deg == 0.0
    assert seg.midpoint == Point2D(3000.0, 1000.0)

def test_polygon_shoelace_area():
    # 6m x 4m rectangle = 6000mm x 4000mm = 24,000,000 mm² = 24.0 sqm
    vertices = [
        Point2D(0, 0),
        Point2D(6000, 0),
        Point2D(6000, 4000),
        Point2D(0, 4000)
    ]
    poly = Polygon2D(vertices=vertices)
    assert poly.gross_area_mm2 == 24_000_000.0
    assert poly.perimeter_mm == 20_000.0
    assert poly.centroid == Point2D(3000.0, 2000.0)

def test_polygon_with_interior_hole():
    # 6m x 4m outer boundary (24 sqm)
    outer = [
        Point2D(0, 0),
        Point2D(6000, 0),
        Point2D(6000, 4000),
        Point2D(0, 4000)
    ]
    # 1m x 1m column cutout (1 sqm)
    hole = [
        Point2D(2000, 1000),
        Point2D(3000, 1000),
        Point2D(3000, 2000),
        Point2D(2000, 2000)
    ]
    poly = Polygon2D(vertices=outer, holes=[hole])
    assert poly.gross_area_mm2 == 24_000_000.0
    assert poly.holes_area_mm2 == 1_000_000.0
    assert poly.net_area_mm2 == 23_000_000.0

def test_point_in_polygon_raycasting():
    vertices = [
        Point2D(0, 0),
        Point2D(5000, 0),
        Point2D(5000, 5000),
        Point2D(0, 5000)
    ]
    poly = Polygon2D(vertices=vertices)
    # Inside
    assert poly.contains_point(Point2D(2500, 2500)) is True
    # Outside
    assert poly.contains_point(Point2D(6000, 2500)) is False
    assert poly.contains_point(Point2D(-100, 2500)) is False
