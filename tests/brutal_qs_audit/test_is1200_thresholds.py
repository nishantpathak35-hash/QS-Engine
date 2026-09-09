"""
Brutal Real-Life QS Audit — IS 1200 Statutory Deduction Thresholds
Authored by: Er. Rajeev Sharma (Chief QS, 25+ Years Experience)
Enforces:
1. IS 1200 Part 7 (Ceilings): Openings <= 0.40 sqm are NOT deducted.
2. IS 1200 Part 11 (Flooring): Door threshold rebate additions & void thresholds.
"""

import pytest
from core.geometry.primitives import Point2D, Polygon2D
from core.models.semantics import Opening, OpeningType
from qs.is1200_rules import IS1200TradeRules

def test_is1200_ceiling_diffuser_vs_shaft_deduction():
    """
    BRUTAL CONTRACTOR TRAP:
    Amateur QS software deducts every cutout on a ceiling plan, costing contractors lakhs.
    Statutory IS 1200 Clause 4.1.1 dictates:
    - 4 AC supply diffusers (600x600mm = 0.36 sqm each <= 0.40 sqm) -> NO DEDUCTION!
    - 1 Structural MEP Duct Shaft (1200x1200mm = 1.44 sqm > 0.40 sqm) -> DEDUCT!
    Room: 10m x 5m = 50.000 sqm gross ceiling.
    Expected Net Ceiling: 50.0 - 1.44 = 48.560 sqm (NOT 50 - 4*0.36 - 1.44 = 47.12 sqm!).
    """
    # 10m x 5m room polygon
    room_poly = Polygon2D(vertices=[
        Point2D(0, 0),
        Point2D(10000, 0),
        Point2D(10000, 5000),
        Point2D(0, 5000)
    ])

    # 4 AC diffusers (600mm x 600mm = 0.36 sqm)
    diffusers = [
        Polygon2D([Point2D(1000 + i*2000, 1000), Point2D(1600 + i*2000, 1000),
                   Point2D(1600 + i*2000, 1600), Point2D(1000 + i*2000, 1600)])
        for i in range(4)
    ]

    # 1 large duct shaft (1200mm x 1200mm = 1.44 sqm)
    shaft = Polygon2D([
        Point2D(8000, 3000), Point2D(9200, 3000),
        Point2D(9200, 4200), Point2D(8000, 4200)
    ])

    all_cutouts = diffusers + [shaft]

    res = IS1200TradeRules.calculate_ceiling_with_thresholds(room_poly, all_cutouts)

    # Gross ceiling must be exactly 50 sqm
    assert res.gross_area_sqm == 50.0

    # Ignored openings must equal 4 diffusers * 0.36 sqm = 1.44 sqm
    assert pytest.approx(res.ignored_openings_sqm, abs=0.001) == 1.44

    # Deducted openings must ONLY be the 1.44 sqm shaft
    assert pytest.approx(res.deducted_openings_sqm, abs=0.001) == 1.44

    # Net ceiling must be 48.560 sqm
    assert pytest.approx(res.net_ceiling_area_sqm, abs=0.001) == 48.560

def test_is1200_flooring_door_rebate_extension():
    """
    BRUTAL CONTRACTOR TRAP:
    Floor finish extends past the wall line into the door opening under the shutter.
    For a 10m x 5m room (50 sqm) with two 1000mm doors in 150mm walls:
    Rebate addition per door: 1.0m width * 0.075m depth = +0.075 sqm.
    Total addition: 2 * 0.075 = +0.150 sqm.
    Expected Net Flooring: 50.150 sqm.
    """
    room_poly = Polygon2D(vertices=[
        Point2D(0, 0), Point2D(10000, 0),
        Point2D(10000, 5000), Point2D(0, 5000)
    ])

    doors = [
        Opening(id="D1", opening_type=OpeningType.DOOR, width_m=1.0),
        Opening(id="D2", opening_type=OpeningType.DOOR, width_m=1.0)
    ]

    res = IS1200TradeRules.calculate_flooring_with_door_rebates(
        room_poly=room_poly,
        floor_cutouts=[],
        doors=doors,
        door_jamb_depth_mm=75.0
    )

    assert res.room_polygon_area_sqm == 50.0
    assert pytest.approx(res.door_rebates_added_sqm, abs=0.001) == 0.150
    assert pytest.approx(res.net_flooring_area_sqm, abs=0.001) == 50.150
