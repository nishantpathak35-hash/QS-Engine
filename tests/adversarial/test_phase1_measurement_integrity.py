"""
Adversarial Tests — Phase-1 Measurement Integrity & True YAML Rule Execution
Validates:
1. Missing door width does NOT deduct from skirting without approved project assumption.
2. Skirting item status becomes REVIEW_REQUIRED when door dimensions are missing.
3. Setting deduct_openings: false completely disables opening deductions.
4. Removing a rule from YAML results in zero quantities generated for that rule.
5. Decoupling of room names from materials: no Vitrified Tile without finish evidence.
6. ProjectProfile configuration controls approved assumptions.
"""

import pytest
from pathlib import Path
from core.geometry.primitives import Point2D, Polygon2D, Segment2D
from core.models.semantics import Room, Opening, OpeningType, EntityStatus
from core.models.project_profile import ProjectProfile
from parsers.dxf.reader import ExtractedBlock
from semantics.openings.door_detector import DoorDetector
from qs.rule_engine import QSRuleEngine


def test_missing_door_width_does_not_deduct_skirting():
    """Unapproved missing door width must NOT deduct 0.90m from skirting."""
    room = Room(
        id="R-01",
        name="DIRECTOR ROOM",
        polygon=Polygon2D([Point2D(0, 0), Point2D(5000, 0), Point2D(5000, 4000), Point2D(0, 4000)]),
        skirting_finish_code="SK-01"
    )
    # Perimeter = 18.0 m
    # Door on boundary has width_m = None (missing dimension)
    door = Opening(
        id="DR-001",
        opening_type=OpeningType.DOOR,
        location=Point2D(2500, 0),
        width_m=None,
        height_m=None,
        is_provisional=True,
        status=EntityStatus.REVIEW_REQUIRED
    )

    rule_engine = QSRuleEngine()
    takeoff = rule_engine.calculate_takeoff("DRW-01", "A-01", "01", [room], openings=[door])

    sk_item = next(it for it in takeoff.items if it.item_code == "SK-01")
    # Gross perimeter is 18.0m. No deduction can be made because width is unknown!
    assert sk_item.quantity == 18.00
    assert len(sk_item.deductions) == 0
    # Dependent status MUST be REVIEW_REQUIRED!
    assert sk_item.status == EntityStatus.REVIEW_REQUIRED


def test_approved_project_assumption_deducts_door():
    """When project explicitly approves default_door_width_m=0.85, deduction occurs and is flagged."""
    profile = ProjectProfile(
        project_id="PRJ-ASSUME",
        allow_assumptions=True,
        approved_assumptions={"default_door_width_m": 0.85, "default_door_height_m": 2.10}
    )
    detector = DoorDetector()
    block = ExtractedBlock(name="DOOR_UNSPECIFIED", location=Point2D(1000, 0), layer="A-DOOR")
    wall = Segment2D(start=Point2D(0, 0), end=Point2D(5000, 0))

    openings, non_doors, exceptions = detector.process_blocks([block], [wall], project_profile=profile)
    assert len(openings) == 1
    assert openings[0].width_m == 0.85
    assert openings[0].is_provisional is True
    assert openings[0].status == EntityStatus.REVIEW_REQUIRED


def test_deduct_openings_false_in_yaml_disables_deductions(tmp_path: Path):
    """Setting deduct_openings: false in YAML profile must stop all opening deductions."""
    custom_yaml = tmp_path / "no_deductions.yaml"
    custom_yaml.write_text("""
profile_id: test_no_deduct
name: Test No Deduct Profile
version: 1.0.0
rules:
  - id: QS-SK-TEST
    item_code: SK-01
    category: skirting
    description: Perimeter Skirting
    unit: m
    target: room
    applies_when:
      skirting_finish_code: "SK-01"
    calculator: is1200.skirting_with_deductions
    deduct_openings: false
""", encoding="utf-8")

    room = Room(
        id="R-01",
        name="LOBBY",
        polygon=Polygon2D([Point2D(0, 0), Point2D(4000, 0), Point2D(4000, 3000), Point2D(0, 3000)]),
        skirting_finish_code="SK-01"
    )
    door = Opening(
        id="DR-01",
        opening_type=OpeningType.DOOR,
        location=Point2D(2000, 0),
        width_m=1.0,
        height_m=2.1
    )

    engine = QSRuleEngine(profile_path=custom_yaml)
    takeoff = engine.calculate_takeoff("DRW-01", "A-01", "01", [room], openings=[door])

    sk_item = next(it for it in takeoff.items if it.item_code == "SK-01")
    # Gross perimeter is 14.0m. Deduction must be 0 because deduct_openings: false
    assert sk_item.quantity == 14.0
    assert len(sk_item.deductions) == 0


def test_removing_rule_from_yaml_generates_zero_quantities(tmp_path: Path):
    """If skirting rule is deleted from YAML, engine must NOT generate any SK-01 item."""
    custom_yaml = tmp_path / "no_skirting.yaml"
    custom_yaml.write_text("""
profile_id: test_no_skirting
name: Test No Skirting Profile
version: 1.0.0
rules:
  - id: QS-FL-TEST
    item_code: FL-01
    category: finishes
    description: Vitrified Tile
    unit: sqm
    target: room
    calculator: generic.polygon_net_area
""", encoding="utf-8")

    room = Room(
        id="R-01",
        name="CABIN",
        polygon=Polygon2D([Point2D(0, 0), Point2D(4000, 0), Point2D(4000, 3000), Point2D(0, 3000)]),
        finish_code="FL-01"
    )

    engine = QSRuleEngine(profile_path=custom_yaml)
    takeoff = engine.calculate_takeoff("DRW-01", "A-01", "01", [room])

    item_codes = [it.item_code for it in takeoff.items]
    assert "SK-01" not in item_codes, "Deleted skirting rule must NOT produce SK-01!"
    assert "FL-01" in item_codes


def test_room_name_does_not_fabricate_finish_without_evidence_or_approval():
    """MEETING ROOM without drawing finish code and without activated assumption produces FL-RAW."""
    room = Room(
        id="R-01",
        name="MEETING ROOM",
        polygon=Polygon2D([Point2D(0, 0), Point2D(5000, 0), Point2D(5000, 4000), Point2D(0, 4000)]),
        finish_code=None
    )
    # Project profile with allow_assumptions = False
    project_profile = ProjectProfile(
        project_id="STRICT-QS",
        allow_assumptions=False
    )
    engine = QSRuleEngine()
    takeoff = engine.calculate_takeoff("DRW-01", "A-01", "01", [room], project_profile=project_profile)

    totals = takeoff.total_by_item()
    assert "FL-01" not in totals, "Must NOT fabricate Vitrified Tile!"
    assert "FL-RAW" in totals
    assert totals["FL-RAW"]["total_quantity"] == 20.0
    raw_item = next(it for it in takeoff.items if it.item_code == "FL-RAW")
    assert raw_item.status == EntityStatus.RAW_MEASURED
