"""
Unit Tests for Single-Room Topology & Boundary Solver Robustness
Directly addresses Audit P0 Finding #1:
Single closed room must NEVER be discarded as an exterior face.
"""

import pytest
from core.geometry.primitives import Point2D, Segment2D
from parsers.dxf.reader import ExtractedText
from semantics.rooms.boundary_solver import RoomBoundarySolver

def test_single_closed_rectangular_room():
    """A drawing containing a single 5000mm x 4000mm room must return exactly 1 room with 20.00 sqm."""
    solver = RoomBoundarySolver()
    
    # 4 boundary wall segments
    walls = [
        Segment2D(start=Point2D(0, 0), end=Point2D(5000, 0)),
        Segment2D(start=Point2D(5000, 0), end=Point2D(5000, 4000)),
        Segment2D(start=Point2D(5000, 4000), end=Point2D(0, 4000)),
        Segment2D(start=Point2D(0, 4000), end=Point2D(0, 0))
    ]
    texts = [
        ExtractedText(content="PRIVATE OFFICE", location=Point2D(2500, 2000), height_mm=250)
    ]

    rooms = solver.solve_rooms(walls, texts)
    assert len(rooms) == 1, "Single enclosed room must NOT be dropped!"
    assert rooms[0].name == "PRIVATE OFFICE"
    assert pytest.approx(rooms[0].net_area_sqm, abs=0.01) == 20.00
    assert pytest.approx(rooms[0].perimeter_m, abs=0.01) == 18.00


def test_single_l_shaped_room():
    """An L-shaped room (8m x 6m bounding, cut out 4m x 3m) must return 1 room with 36.00 sqm."""
    solver = RoomBoundarySolver()
    
    # L-shape: (0,0)->(8000,0)->(8000,3000)->(4000,3000)->(4000,6000)->(0,6000)->(0,0)
    # Area = (8*3) + (4*3) = 24 + 12 = 36 sqm
    pts = [
        Point2D(0, 0), Point2D(8000, 0), Point2D(8000, 3000),
        Point2D(4000, 3000), Point2D(4000, 6000), Point2D(0, 6000)
    ]
    walls = [
        Segment2D(start=pts[i], end=pts[(i + 1) % len(pts)])
        for i in range(len(pts))
    ]
    texts = [
        ExtractedText(content="STUDIO", location=Point2D(2000, 2000), height_mm=250)
    ]

    rooms = solver.solve_rooms(walls, texts)
    assert len(rooms) == 1
    assert rooms[0].name == "STUDIO"
    assert pytest.approx(rooms[0].net_area_sqm, abs=0.01) == 36.00


def test_room_with_interior_column_hole():
    """A room with an interior column island should produce 1 room containing an interior hole."""
    solver = RoomBoundarySolver()
    
    # Room: 10m x 10m = 100 sqm
    outer_pts = [Point2D(0, 0), Point2D(10000, 0), Point2D(10000, 10000), Point2D(0, 10000)]
    walls = [
        Segment2D(start=outer_pts[i], end=outer_pts[(i + 1) % len(outer_pts)])
        for i in range(len(outer_pts))
    ]
    # Interior column: 1m x 1m = 1 sqm at center (4500, 4500) to (5500, 5500)
    col_pts = [Point2D(4500, 4500), Point2D(5500, 4500), Point2D(5500, 5500), Point2D(4500, 5500)]
    for i in range(len(col_pts)):
        walls.append(Segment2D(start=col_pts[i], end=col_pts[(i + 1) % len(col_pts)]))

    texts = [ExtractedText(content="MAIN HALL", location=Point2D(2000, 2000), height_mm=250)]

    rooms = solver.solve_rooms(walls, texts)
    # The outer room should be detected with area = 100 - 1 = 99.00 sqm
    assert len(rooms) == 1
    assert rooms[0].name == "MAIN HALL"
    assert pytest.approx(rooms[0].net_area_sqm, abs=0.01) == 99.00
    assert len(rooms[0].polygon.holes) == 1


def test_outer_envelope_with_multiple_internal_rooms():
    """When an outer site perimeter encompasses multiple rooms, internal rooms are kept, outer hull is dropped."""
    solver = RoomBoundarySolver()

    # Room A: (0,0) to (5000, 5000) = 25 sqm
    # Room B: (5000,0) to (10000, 5000) = 25 sqm
    walls = [
        Segment2D(start=Point2D(0, 0), end=Point2D(5000, 0)),
        Segment2D(start=Point2D(5000, 0), end=Point2D(10000, 0)),
        Segment2D(start=Point2D(10000, 0), end=Point2D(10000, 5000)),
        Segment2D(start=Point2D(10000, 5000), end=Point2D(5000, 5000)),
        Segment2D(start=Point2D(5000, 5000), end=Point2D(0, 5000)),
        Segment2D(start=Point2D(0, 5000), end=Point2D(0, 0)),
        # Dividing partition wall
        Segment2D(start=Point2D(5000, 0), end=Point2D(5000, 5000))
    ]
    texts = [
        ExtractedText(content="ROOM A", location=Point2D(2500, 2500), height_mm=250),
        ExtractedText(content="ROOM B", location=Point2D(7500, 2500), height_mm=250)
    ]

    rooms = solver.solve_rooms(walls, texts)
    assert len(rooms) == 2
    room_names = {r.name for r in rooms}
    assert room_names == {"ROOM A", "ROOM B"}
    for r in rooms:
        assert pytest.approx(r.net_area_sqm, abs=0.01) == 25.00
