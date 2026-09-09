"""
Unit Tests for Block Classification Hierarchy
Directly addresses Audit P0 Finding #2:
Every DXF block must NOT be treated as a door. WORKSTATION must NEVER be deducted from skirting.
"""

from core.geometry.primitives import Point2D, Segment2D, Polygon2D
from core.models.semantics import Room
from parsers.dxf.reader import ExtractedBlock
from parsers.dxf.block_classifier import BlockClassifier, BlockCategory
from semantics.openings.door_detector import DoorDetector
from qs.rule_engine import QSRuleEngine

def test_workstation_is_not_treated_as_door():
    """A WORKSTATION block must be classified as FURNITURE and NEVER become a door."""
    classifier = BlockClassifier()
    block = ExtractedBlock(
        name="WORKSTATION_1200x600",
        location=Point2D(2000, 2000),
        layer="F-FURN"
    )
    result = classifier.classify(block)
    assert result.category == BlockCategory.FURNITURE
    assert result.is_door is False


def test_furniture_and_fixtures_hierarchy():
    """Chairs, desks, tables, and sanitary fixtures must never be doors."""
    classifier = BlockClassifier()
    test_cases = [
        ("DESK_EXECUTIVE", "0", BlockCategory.FURNITURE),
        ("CHAIR_TASK", "FURN", BlockCategory.FURNITURE),
        ("CONFERENCE_TABLE_10PAX", "A-FURN", BlockCategory.FURNITURE),
        ("SOFA_3SEATER", "I-FURN", BlockCategory.FURNITURE),
        ("WC_WALL_HUNG", "P-SANR", BlockCategory.FIXTURE),
        ("WASH_BASIN_COUNTER", "PLUMBING", BlockCategory.FIXTURE),
    ]
    for name, layer, expected_cat in test_cases:
        block = ExtractedBlock(name=name, location=Point2D(100, 100), layer=layer)
        res = classifier.classify(block)
        assert res.category == expected_cat
        assert res.is_door is False


def test_door_identification_hierarchy():
    """Known door layers, door name patterns, and tags must resolve to DOORS with width."""
    classifier = BlockClassifier()

    # 1. Door block on standard layer
    b1 = ExtractedBlock(name="DOOR_900_SINGLE", location=Point2D(0, 0), layer="A-DOOR")
    res1 = classifier.classify(b1)
    assert res1.is_door is True
    assert res1.category == BlockCategory.DOOR
    assert res1.detected_width_m == 0.90

    # 2. Door block with width attribute
    b2 = ExtractedBlock(
        name="D1", location=Point2D(0, 0), layer="0",
        attributes={"TYPE": "DOOR", "WIDTH": "1000mm"}
    )
    res2 = classifier.classify(b2)
    assert res2.is_door is True
    assert res2.detected_width_m == 1.00


def test_unknown_block_triggers_exception():
    """Unrecognized block name and layer must yield UNKNOWN category and trigger UNKNOWN_BLOCK exception."""
    classifier = BlockClassifier()
    b_unknown = ExtractedBlock(name="CUSTOM_EQUIPMENT_XYZ", location=Point2D(500, 500), layer="SPECIAL_01")
    res = classifier.classify(b_unknown)
    assert res.category == BlockCategory.UNKNOWN
    assert res.is_door is False

    detector = DoorDetector(classifier)
    openings, non_doors, exceptions = detector.process_blocks([b_unknown], wall_segments=[])
    assert len(openings) == 0
    assert len(exceptions) == 1
    assert exceptions[0]["code"] == "UNKNOWN_BLOCK"
    assert "CUSTOM_EQUIPMENT_XYZ" in exceptions[0]["message"]


def test_skirting_does_not_deduct_workstation():
    """Verify that placing 4 workstations along the perimeter of a room causes ZERO skirting deduction."""
    room = Room(
        id="R-01",
        name="OPEN OFFICE",
        polygon=Polygon2D([Point2D(0, 0), Point2D(10000, 0), Point2D(10000, 8000), Point2D(0, 8000)]),
        skirting_finish_code="SK-01"
    )
    # Perimeter = 36.00 m
    # 4 Workstations placed along the wall at (2000, 0), (4000, 0), (6000, 0), (8000, 0)
    blocks = [
        ExtractedBlock(name="WORKSTATION_1200", location=Point2D(2000, 0), layer="F-FURN"),
        ExtractedBlock(name="WORKSTATION_1200", location=Point2D(4000, 0), layer="F-FURN"),
        ExtractedBlock(name="WORKSTATION_1200", location=Point2D(6000, 0), layer="F-FURN"),
        ExtractedBlock(name="WORKSTATION_1200", location=Point2D(8000, 0), layer="F-FURN"),
    ]
    walls = [
        Segment2D(start=Point2D(0, 0), end=Point2D(10000, 0)),
        Segment2D(start=Point2D(10000, 0), end=Point2D(10000, 8000)),
        Segment2D(start=Point2D(10000, 8000), end=Point2D(0, 8000)),
        Segment2D(start=Point2D(0, 8000), end=Point2D(0, 0)),
    ]

    detector = DoorDetector()
    openings, non_doors, exceptions = detector.process_blocks(blocks, walls)

    # Must be 0 doors detected
    assert len(openings) == 0
    assert len(non_doors) == 4

    rule_engine = QSRuleEngine()
    takeoff = rule_engine.calculate_takeoff(
        drawing_id="DRW-01",
        drawing_number="A-01",
        revision="01",
        rooms=[room],
        openings=openings,
        blocks=blocks
    )

    totals = takeoff.total_by_item()
    # Gross perimeter is 36.00m. Since no doors exist, net skirting MUST be exactly 36.00m (ZERO deduction for workstations!)
    assert totals["SK-01"]["total_quantity"] == 36.00
