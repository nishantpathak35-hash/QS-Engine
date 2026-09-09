"""
Adversarial Test Suite: Material Evidence, Applicability & Door Subtype Routing
Enforces Phase-1 Production Hardening Audit Items 1, 2, 3, 4, 5, 16, 17, 18, 19.
"""

import pytest
from pathlib import Path
from core.geometry.primitives import Point2D, Polygon2D
from core.models.semantics import Room, Opening, OpeningType, EntityStatus, BlockInstance
from core.models.project_profile import ProjectProfile
from qs.rule_engine import QSRuleEngine


def test_meeting_room_without_finish_produces_raw_measured():
    """A room called MEETING ROOM with no finish evidence must produce FL-RAW and raise UNKNOWN_FLOOR_FINISH."""
    room = Room(
        id="R-01",
        name="MEETING ROOM",
        polygon=Polygon2D([Point2D(0, 0), Point2D(6000, 0), Point2D(6000, 4000), Point2D(0, 4000)]),
        finish_code=None
    )
    engine = QSRuleEngine()
    takeoff = engine.calculate_takeoff("DRW-01", "A-01", "01", [room])

    totals = takeoff.total_by_item()
    assert "FL-01" not in totals, "Must NOT guess FL-01 Vitrified Tile Flooring from room name alone!"
    assert "FL-RAW" in totals, "Must produce FL-RAW to preserve geometry authority!"
    assert totals["FL-RAW"]["total_quantity"] == 24.0

    exc_codes = [e["code"] for e in takeoff.exceptions]
    assert "UNKNOWN_FLOOR_FINISH" in exc_codes
    assert "UNKNOWN_CEILING_FINISH" in exc_codes


def test_meeting_room_with_f01_produces_fl01():
    """When drawing provides explicit finish code 'F-01', engine maps to FL-01."""
    room = Room(
        id="R-01",
        name="MEETING ROOM",
        polygon=Polygon2D([Point2D(0, 0), Point2D(6000, 0), Point2D(6000, 4000), Point2D(0, 4000)]),
        finish_code="F-01"
    )
    engine = QSRuleEngine()
    takeoff = engine.calculate_takeoff("DRW-01", "A-01", "01", [room])

    totals = takeoff.total_by_item()
    assert "FL-01" in totals
    assert totals["FL-01"]["total_quantity"] == 24.0
    assert "FL-RAW" not in totals


def test_meeting_room_with_f02_produces_fl02_in_commercial_profile():
    """When drawing provides finish code 'CP-01' in commercial profile, engine maps to FL-02 Carpet Tiles."""
    profile_path = Path(__file__).parents[2] / "qs" / "profiles" / "commercial_fitout.yaml"
    engine = QSRuleEngine(profile_path=profile_path)
    room = Room(
        id="R-01",
        name="MEETING ROOM",
        polygon=Polygon2D([Point2D(0, 0), Point2D(6000, 0), Point2D(6000, 4000), Point2D(0, 4000)]),
        finish_code="CP-01"
    )
    takeoff = engine.calculate_takeoff("DRW-01", "A-01", "01", [room])

    totals = takeoff.total_by_item()
    assert "FL-02" in totals
    assert totals["FL-02"]["total_quantity"] == 24.0
    assert "FL-01" not in totals


def test_unknown_finish_code_produces_raw_and_exception():
    """When drawing provides unrecognized finish code 'XYZ-99', produce FL-RAW and exception."""
    room = Room(
        id="R-01",
        name="LAB",
        polygon=Polygon2D([Point2D(0, 0), Point2D(5000, 0), Point2D(5000, 4000), Point2D(0, 4000)]),
        finish_code="XYZ-99"
    )
    engine = QSRuleEngine()
    takeoff = engine.calculate_takeoff("DRW-01", "A-01", "01", [room])

    totals = takeoff.total_by_item()
    assert "FL-RAW" in totals
    exc_codes = [e["code"] for e in takeoff.exceptions]
    assert "UNKNOWN_FLOOR_FINISH" in exc_codes


def test_skirting_applicability_prevents_duplicate_quantities():
    """In commercial profile with SK-01 and SK-02, room with SK-01 MUST NOT also produce SK-02."""
    profile_path = Path(__file__).parents[2] / "qs" / "profiles" / "commercial_fitout.yaml"
    engine = QSRuleEngine(profile_path=profile_path)

    # Room 1 is eligible for SK-01 only
    room1 = Room(
        id="R-01",
        name="CONFERENCE",
        polygon=Polygon2D([Point2D(0, 0), Point2D(5000, 0), Point2D(5000, 4000), Point2D(0, 4000)]),
        finish_code="F-01",
        skirting_finish_code="SK-01"
    )
    # Room 2 is eligible for SK-02 only
    room2 = Room(
        id="R-02",
        name="CORRIDOR",
        polygon=Polygon2D([Point2D(10000, 0), Point2D(14000, 0), Point2D(14000, 3000), Point2D(10000, 3000)]),
        finish_code="CP-01",
        skirting_finish_code="SK-02"
    )
    # Room 3 has no skirting mapping
    room3 = Room(
        id="R-03",
        name="STORE",
        polygon=Polygon2D([Point2D(20000, 0), Point2D(23000, 0), Point2D(23000, 2000), Point2D(20000, 2000)]),
        finish_code=None,
        skirting_finish_code=None
    )

    takeoff = engine.calculate_takeoff("DRW-01", "A-01", "01", [room1, room2, room3])
    totals = takeoff.total_by_item()

    # Room 1 perimeter = 18m -> only SK-01
    assert totals["SK-01"]["total_quantity"] == 18.00
    assert totals["SK-01"]["count"] == 1

    # Room 2 perimeter = 14m -> only SK-02
    assert totals["SK-02"]["total_quantity"] == 14.00
    assert totals["SK-02"]["count"] == 1

    # Room 3 perimeter = 10m -> neither SK-01 nor SK-02 generated!
    # Total count across skirting must be exactly 2 (Room 1 and Room 2)
    skirting_locations = [it.location for it in takeoff.items if "SK" in it.item_code]
    assert "STORE" not in skirting_locations
    assert "UNKNOWN_SKIRTING_FINISH" in [e["code"] for e in takeoff.exceptions]


def test_door_subtypes_route_to_distinct_boq_items():
    """Single-leaf, double-leaf, glass doors map to DR-01, DR-02, DR-03 respectively."""
    profile_path = Path(__file__).parents[2] / "qs" / "profiles" / "commercial_fitout.yaml"
    engine = QSRuleEngine(profile_path=profile_path)

    openings = [
        # Single Leaf Flush Door
        Opening(id="D1", opening_type=OpeningType.DOOR, door_type="single_leaf", width_m=0.90, height_m=2.10),
        Opening(id="D2", opening_type=OpeningType.DOOR, door_type="single_leaf", width_m=1.00, height_m=2.10),
        # Double Leaf Flush Door
        Opening(id="D3", opening_type=OpeningType.DOOR, door_type="double_leaf", width_m=1.80, height_m=2.10),
        # Frameless Glass Door
        Opening(id="D4", opening_type=OpeningType.DOOR, door_type="glass", material="glass", width_m=1.20, height_m=2.40),
        # Unclassified door subtype
        Opening(id="D5", opening_type=OpeningType.DOOR, door_type="unknown", width_m=1.10, height_m=2.10)
    ]

    takeoff = engine.calculate_takeoff("DRW-01", "A-01", "01", rooms=[], openings=openings)
    totals = takeoff.total_by_item()

    assert totals["DR-01"]["total_quantity"] == 2.0  # D1, D2
    assert totals["DR-02"]["total_quantity"] == 1.0  # D3
    assert totals["DR-03"]["total_quantity"] == 1.0  # D4
    assert totals["DR-UNKNOWN"]["total_quantity"] == 1.0  # D5

    # D5 must have REVIEW_REQUIRED status
    d5_item = next(it for it in takeoff.items if it.item_code == "DR-UNKNOWN")
    assert d5_item.status == EntityStatus.REVIEW_REQUIRED
    assert "UNKNOWN_DOOR_SUBTYPE" in [e["code"] for e in takeoff.exceptions]
