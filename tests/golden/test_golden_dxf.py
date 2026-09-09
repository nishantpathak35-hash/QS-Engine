"""
Golden Drawing Regression Test
Validates end-to-end DXF ingestion -> Room solving -> QS Takeoff against known CAD ground-truth.
Enforces Blueprint Section 49 & Section 51 (Room Area Accuracy > 99%).
"""

import pytest
from pathlib import Path
from tests.fixtures.synthetic_dxf import create_synthetic_office_dxf
from parsers.dxf.reader import DXFParser
from parsers.dxf.layer_classifier import LayerCategory, LayerMappingProfile
from semantics.rooms.boundary_solver import RoomBoundarySolver
from qs.rule_engine import QSRuleEngine
from core.models.semantics import Opening, OpeningType
from core.geometry.primitives import Point2D

def test_golden_synthetic_office_takeoff(tmp_path: Path):
    # 1. Generate known benchmark DXF
    dxf_file = tmp_path / "golden_office.dxf"
    create_synthetic_office_dxf(dxf_file)

    # 2. Parse DXF
    parser = DXFParser()
    parsed = parser.parse_file(dxf_file)

    assert parsed.scale_to_mm == 1.0
    assert "A-WALL" in parsed.layers
    assert len(parsed.texts) == 6  # 2 room labels + 2 floor finish codes + 2 skirting finish codes
    assert len(parsed.blocks) == 2

    # 3. Extract Wall Segments
    wall_segments = parsed.get_segments_by_category(LayerCategory.WALL, parser.layer_profile)
    assert len(wall_segments) > 0

    # 4. Extract Openings from door blocks
    openings = [
        Opening(
            id=f"OP-{i+1}",
            opening_type=OpeningType.DOOR,
            width_m=0.90,
            location=b.location,
            tag="D1"
        )
        for i, b in enumerate(parsed.blocks)
    ]

    # 5. Solve Room Boundaries (with door opening closures)
    solver = RoomBoundarySolver()
    rooms = solver.solve_rooms(wall_segments, parsed.texts, door_openings=openings)

    # Must detect exactly 2 rooms
    assert len(rooms) == 2
    room_dict = {r.name: r for r in rooms}
    assert "CONFERENCE ROOM" in room_dict
    assert "EXECUTIVE CABIN" in room_dict

    conf_room = room_dict["CONFERENCE ROOM"]
    cabin = room_dict["EXECUTIVE CABIN"]

    # Ground-truth assertions:
    # Conference Room: 6m x 4m = 24.000 sqm
    assert pytest.approx(conf_room.net_area_sqm, abs=0.01) == 24.0
    assert pytest.approx(conf_room.perimeter_m, abs=0.01) == 20.0

    # Executive Cabin: 4m x 4m = 16.000 sqm
    assert pytest.approx(cabin.net_area_sqm, abs=0.01) == 16.0
    assert pytest.approx(cabin.perimeter_m, abs=0.01) == 16.0

    # 6. Run QS Rule Engine
    rule_engine = QSRuleEngine()
    takeoff = rule_engine.calculate_takeoff(
        drawing_id="DRW-GOLDEN-01",
        drawing_number="A-101",
        revision="01",
        rooms=rooms,
        openings=openings,
        blocks=[
            b for b in parsed.blocks
        ]
    )

    totals = takeoff.total_by_item()

    # Flooring: 24.0 sqm (Conference) + 16.0 sqm (Cabin) = 40.0 sqm
    assert totals["FL-01"]["total_quantity"] == 40.0
    assert totals["FL-01"]["unit"] == "sqm"

    # Skirting:
    # Conf Room: 20m - 0.9m door = 19.10m
    # Cabin: 16m - 0.9m door = 15.10m
    # Total Skirting = 34.20m
    assert totals["SK-01"]["total_quantity"] == 34.20
    assert totals["SK-01"]["unit"] == "m"

    # Doors: exactly 2 Nos
    assert totals["DR-01"]["total_quantity"] == 2.0
    assert totals["DR-01"]["unit"] == "nos"
