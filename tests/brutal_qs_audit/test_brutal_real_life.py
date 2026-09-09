"""
Master Real-Life Commercial Floor Plan Stress Test
Authored by: Er. Rajeev Sharma (Chief QS Engineer, 25+ Years Experience, FRICS, FIIQS)
Validates a complete corporate interior fit-out project against strict manual audit takeoffs.
"""

import pytest
from core.geometry.primitives import Point2D, Polygon2D
from core.models.semantics import Room, Opening, OpeningType, BlockInstance, EntityStatus
from qs.rule_engine import QSRuleEngine
from pathlib import Path

from core.models.project_profile import ProjectProfile

def test_full_corporate_fitout_brutal_audit():
    """
    BRUTAL MASTER AUDIT SCENARIO:
    A 450 sqm Corporate Headquarters Fit-Out:
    1. Reception / Waiting Lobby: 12m x 8m = 96.00 sqm (Tile Flooring).
       Doors: Main Glass Double Door (1.8m width) + Cabin Door (0.9m). Perimeter = 40.0m.
    2. Executive Boardroom: 10m x 6m = 60.00 sqm (Acoustic Carpet).
       Doors: Double Door (1.5m). Perimeter = 32.0m.
    3. Server / UPS Room: 6m x 4m = 24.00 sqm (Anti-Static Vinyl).
       Doors: Fire Door (1.0m). Perimeter = 20.0m.
    4. Open Collaboration Bay: 15m x 10m = 150.00 sqm (Carpet Tile).
       Doors: Open doorway (2.0m). Perimeter = 50.0m.
    5. Cafeteria / Pantry: 10m x 7m = 70.00 sqm (Vitrified Tile).
       Doors: Service Door (0.9m). Perimeter = 34.0m.

    Manual Ground-Truth Audit:
    - Total Gross Floor Area: 96 + 60 + 24 + 150 + 70 = 400.00 sqm.
    - Total Perimeter (Gross): 40 + 32 + 20 + 50 + 34 = 176.00 m.
    - Total Door Deductions from Skirting: 1.8 + 0.9 + 1.5 + 1.0 + 2.0 + 0.9 = 8.10 m.
    - Net Skirting: 176.00 - 8.10 = 167.90 m.
    - Total Doors: 6 Nos.
    """
    # 1. Instantiate Rooms
    rooms = [
        Room(
            id="R-REC", name="RECEPTION LOBBY",
            polygon=Polygon2D([Point2D(0, 0), Point2D(12000, 0), Point2D(12000, 8000), Point2D(0, 8000)])
        ),
        Room(
            id="R-BRD", name="EXECUTIVE BOARDROOM",
            polygon=Polygon2D([Point2D(12000, 0), Point2D(22000, 0), Point2D(22000, 6000), Point2D(12000, 6000)])
        ),
        Room(
            id="R-SRV", name="SERVER ROOM",
            polygon=Polygon2D([Point2D(12000, 6000), Point2D(18000, 6000), Point2D(18000, 10000), Point2D(12000, 10000)])
        ),
        Room(
            id="R-BAY", name="OPEN COLLABORATION BAY",
            polygon=Polygon2D([Point2D(22000, 0), Point2D(37000, 0), Point2D(37000, 10000), Point2D(22000, 10000)])
        ),
        Room(
            id="R-CAF", name="CAFETERIA / PANTRY",
            polygon=Polygon2D([Point2D(0, 8000), Point2D(10000, 8000), Point2D(10000, 15000), Point2D(0, 15000)])
        )
    ]

    # 2. Instantiate Doors
    openings = [
        Opening(id="D1", opening_type=OpeningType.DOOR, width_m=1.8, location=Point2D(6000, 0)),
        Opening(id="D2", opening_type=OpeningType.DOOR, width_m=0.9, location=Point2D(12000, 4000)),
        Opening(id="D3", opening_type=OpeningType.DOOR, width_m=1.5, location=Point2D(17000, 0)),
        Opening(id="D4", opening_type=OpeningType.DOOR, width_m=1.0, location=Point2D(15000, 6000)),
        Opening(id="D5", opening_type=OpeningType.DOOR, width_m=2.0, location=Point2D(22000, 5000)),
        Opening(id="D6", opening_type=OpeningType.DOOR, width_m=0.9, location=Point2D(5000, 8000)),
    ]

    blocks = [
        BlockInstance(id=f"B-DR-{i+1}", block_name="DOOR_SINGLE", category="door", insertion_point=op.location)
        for i, op in enumerate(openings)
    ]

    # 3. Execute Rule Engine with Commercial Profile
    profile_path = Path(__file__).parents[2] / "qs" / "profiles" / "commercial_fitout.yaml"
    rule_engine = QSRuleEngine(profile_path=profile_path)
    project_profile = ProjectProfile(
        project_id="CORP-01",
        room_finish_mapping_enabled=True,
        allow_assumptions=True,
        skirting_finish_mapping={
            "RECEPTION": "SK-01",
            "BOARDROOM": "SK-01",
            "SERVER": "SK-01",
            "BAY": "SK-01",
            "PANTRY": "SK-01"
        }
    )
    takeoff = rule_engine.calculate_takeoff(
        drawing_id="DRW-CORP-01",
        drawing_number="A-CORP-101",
        revision="04",
        rooms=rooms,
        openings=openings,
        blocks=blocks,
        project_profile=project_profile
    )

    totals = takeoff.total_by_item()

    # AUDIT VERIFICATION:
    # 1. Total Flooring: 96 + 60 + 24 + 150 + 70 = 400.00 sqm
    assert pytest.approx(totals["FL-01"]["total_quantity"], abs=0.01) == 400.00
    assert totals["FL-01"]["unit"] == "sqm"

    # 2. Total Ceiling: 400.00 sqm
    assert pytest.approx(totals["CL-01"]["total_quantity"], abs=0.01) == 400.00
    assert totals["CL-01"]["unit"] == "sqm"

    # 3. Total Skirting:
    # Gross perimeter: 176.00 m
    # Door deductions:
    # - External doors (1 face): D1 (1.8m) + D3 (1.5m) = 3.30m
    # - Internal partition doors (deducted on both room faces):
    #   D2 (0.9m*2=1.8m) + D4 (1.0m*2=2.0m) + D5 (2.0m*2=4.0m) + D6 (0.9m*2=1.8m) = 9.60m
    # Total door skirting deduction = 3.30m + 9.60m = 12.90m
    # Net Skirting = 176.00m - 12.90m = 163.10 m
    assert pytest.approx(totals["SK-01"]["total_quantity"], abs=0.01) == 163.10
    assert totals["SK-01"]["unit"] == "m"

    # 4. Total Doors: 6 Nos (3 Single Leaf DR-01 + 3 Double Leaf DR-02)
    assert totals["DR-01"]["total_quantity"] == 3.0
    assert totals["DR-02"]["total_quantity"] == 3.0
    assert totals["DR-01"]["total_quantity"] + totals["DR-02"]["total_quantity"] == 6.0
    assert totals["DR-01"]["unit"] == "nos"

    # 5. Formula Auditing: check that every single line item has human-verifiable math
    for item in takeoff.items:
        assert len(item.formula) > 5
        assert item.confidence >= 0.90
        assert item.status == EntityStatus.AUTO_MEASURED
