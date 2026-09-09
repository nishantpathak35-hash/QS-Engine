"""
Brutal Real-Life QS Audit — Complex Geometry, Column Pilasters & L-Shaped Spaces
Authored by: Er. Rajeev Sharma (Chief QS, 25+ Years Experience)
"""

import pytest
from core.geometry.primitives import Point2D, Polygon2D
from core.models.semantics import Opening, OpeningType
from qs.is1200_rules import IS1200TradeRules

def test_l_shaped_boardroom_with_structural_column():
    """
    BRUTAL ARCHITECTURAL CASE:
    Non-rectangular L-shaped Boardroom:
    Main body: 8000mm x 6000mm with a 4000mm x 3000mm cutout in top-right corner.
    Gross Area: (8m * 6m) - (4m * 3m) = 48 - 12 = 36.000 sqm.
    Outer Perimeter: 8 + 6 + 4 + 3 + 4 + 3 = 28.000 m.

    Interior Column: 600mm x 450mm = 0.270 sqm (exceeds 0.20 sqm threshold).
    - Net Floor Area: 36.000 - 0.270 = 35.730 sqm.
    - Door: 1200mm double-leaf door.
    - Net Skirting: 28.000m - 1.200m = 26.800 m.
    """
    # L-shaped boardroom vertices
    l_vertices = [
        Point2D(0, 0),
        Point2D(8000, 0),
        Point2D(8000, 3000),
        Point2D(4000, 3000),
        Point2D(4000, 6000),
        Point2D(0, 6000)
    ]

    boardroom = Polygon2D(vertices=l_vertices)

    # Assert Shoelace math on non-convex L-shape
    assert boardroom.gross_area_mm2 * 1e-6 == 36.000
    assert boardroom.perimeter_mm * 1e-3 == 28.000

    # Structural Column Cutout (600mm x 450mm = 0.270 sqm)
    column_hole = Polygon2D([
        Point2D(1500, 1500), Point2D(2100, 1500),
        Point2D(2100, 1950), Point2D(1500, 1950)
    ])

    door = Opening(id="DR-DBL", opening_type=OpeningType.DOOR, width_m=1.20)

    # 1. Test Flooring calculation
    res_floor = IS1200TradeRules.calculate_flooring_with_door_rebates(
        room_poly=boardroom,
        floor_cutouts=[column_hole],
        doors=[door],
        door_jamb_depth_mm=0.0  # flush threshold reducer
    )

    assert pytest.approx(res_floor.deducted_voids_sqm, abs=0.001) == 0.270
    assert pytest.approx(res_floor.net_flooring_area_sqm, abs=0.001) == 35.730

    # 2. Test Skirting calculation
    skirting_m, formula = IS1200TradeRules.calculate_skirting_with_columns(
        room_poly=boardroom,
        doors=[door]
    )

    assert pytest.approx(skirting_m, abs=0.001) == 26.800
    assert "28.000m" in formula
    assert "1.200m" in formula
