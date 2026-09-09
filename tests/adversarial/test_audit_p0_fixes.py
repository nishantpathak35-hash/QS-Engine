"""
Adversarial Regression Test Suite for Technical Audit 2 P0 Fixes
Guarantees zero regressions against:
1. Unitless DXF blocking without silent mm assumption
2. Inch & Meter scaling accuracy
3. Opening dimensions: MISSING_OPENING_WIDTH and MISSING_OPENING_HEIGHT
4. Single Source of Truth: DRESSER block NEVER counted as a door
5. Room label classifier: dimensions (3000) rejected; AMBIGUOUS_ROOM_LABEL raised
6. Elimination of fabricated finishes: unassigned rooms generate FL-RAW and UNKNOWN_FLOOR_FINISH
"""

from pathlib import Path
import pytest
import ezdxf
from fastapi.testclient import TestClient

from core.geometry.primitives import Point2D, Segment2D, Polygon2D
from core.models.semantics import Room, Opening, OpeningType, EntityStatus
from parsers.dxf.reader import DXFParser, ExtractedBlock, ExtractedText
from parsers.dxf.block_classifier import BlockClassifier, BlockCategory
from semantics.openings.door_detector import DoorDetector
from semantics.rooms.boundary_solver import RoomBoundarySolver
from qs.rule_engine import QSRuleEngine
from apps.api.main import app

client = TestClient(app)

# --------------------------------------------------------------------------
# 1. UNIT HANDLING & ZERO SILENT ASSUMPTIONS
# --------------------------------------------------------------------------

def test_unitless_dxf_blocks_in_api(tmp_path: Path):
    """API process on a unitless DXF ($INSUNITS=0) without assumed_units must halt finalization."""
    dxf_path = tmp_path / "unitless_raw.dxf"
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 0
    msp = doc.modelspace()
    msp.add_line((0, 0), (5000, 0), dxfattribs={"layer": "A-WALL"})
    msp.add_line((5000, 0), (5000, 4000), dxfattribs={"layer": "A-WALL"})
    msp.add_line((5000, 4000), (0, 4000), dxfattribs={"layer": "A-WALL"})
    msp.add_line((0, 4000), (0, 0), dxfattribs={"layer": "A-WALL"})
    doc.saveas(str(dxf_path))

    # Upload
    with open(dxf_path, "rb") as f:
        res_upload = client.post(
            "/v1/drawings/upload",
            files={"file": ("unitless_raw.dxf", f, "application/dxf")},
            data={"drawing_number": "UN-01", "revision": "01"}
        )
    assert res_upload.status_code == 200
    drawing_id = res_upload.json()["drawing_id"]

    # Process without assumed_units -> MUST halt and return empty items with UNIT_REQUIRED exception
    res_proc = client.post(f"/v1/drawings/{drawing_id}/process")
    assert res_proc.status_code == 200
    data = res_proc.json()
    assert len(data["items"]) == 0
    assert any(e["code"] == "UNIT_REQUIRED" for e in data["exceptions"])


def test_explicit_inch_dxf_scaling(tmp_path: Path):
    """DXF with $INSUNITS=1 (Inches) must scale 100 inches to 2540.0 mm."""
    dxf_path = tmp_path / "inches.dxf"
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 1  # 1 = Inches
    msp = doc.modelspace()
    msp.add_line((0, 0), (100, 0), dxfattribs={"layer": "A-WALL"})
    doc.saveas(str(dxf_path))

    parser = DXFParser()
    parsed = parser.parse_file(dxf_path)
    assert parsed.scale_to_mm == 25.4
    seg = parsed.segments[0]
    assert pytest.approx(seg.length_mm, abs=0.01) == 2540.0


def test_explicit_meter_dxf_scaling(tmp_path: Path):
    """DXF with $INSUNITS=6 (Meters) must scale 5 meters to 5000.0 mm."""
    dxf_path = tmp_path / "meters.dxf"
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 6  # 6 = Meters
    msp = doc.modelspace()
    msp.add_line((0, 0), (5, 0), dxfattribs={"layer": "A-WALL"})
    doc.saveas(str(dxf_path))

    parser = DXFParser()
    parsed = parser.parse_file(dxf_path)
    assert parsed.scale_to_mm == 1000.0
    seg = parsed.segments[0]
    assert pytest.approx(seg.length_mm, abs=0.01) == 5000.0


# --------------------------------------------------------------------------
# 2. DOOR SIZING & SINGLE SOURCE OF TRUTH (DRESSER IS NEVER A DOOR)
# --------------------------------------------------------------------------

def test_dresser_is_never_counted_as_door():
    """A block named DRESSER must NEVER become an opening or be counted as a door."""
    blocks = [
        ExtractedBlock(name="DRESSER_BEDROOM", location=Point2D(1000, 1000), layer="F-FURN"),
        ExtractedBlock(name="DRAWER_STORAGE", location=Point2D(2000, 1000), layer="FURNITURE"),
    ]
    detector = DoorDetector()
    openings, non_doors, exceptions = detector.process_blocks(blocks, wall_segments=[])
    
    # 0 doors detected
    assert len(openings) == 0
    assert len(non_doors) == 2

    # Run QSRuleEngine: it must NOT find any doors despite blocks having 'dr' in name
    rule_engine = QSRuleEngine()
    room = Room(id="R-01", name="BEDROOM", polygon=Polygon2D([Point2D(0,0), Point2D(4000,0), Point2D(4000,4000), Point2D(0,4000)]))
    takeoff = rule_engine.calculate_takeoff("D-01", "A-01", "01", [room], openings=openings, blocks=blocks)

    totals = takeoff.total_by_item()
    assert "DR-01" not in totals, "DRESSER / DRAWER must NEVER create a door quantity!"


def test_door_missing_dimensions_logs_exceptions():
    """Door candidate on A-DOOR without width/height attributes must log MISSING_OPENING_WIDTH & MISSING_OPENING_HEIGHT."""
    blocks = [
        ExtractedBlock(name="DOOR_UNSPECIFIED", location=Point2D(0, 0), layer="A-DOOR")
    ]
    detector = DoorDetector()
    openings, non_doors, exceptions = detector.process_blocks(blocks, wall_segments=[])

    assert len(openings) == 1
    assert openings[0].status == EntityStatus.REVIEW_REQUIRED
    exc_codes = [e["code"] for e in exceptions]
    assert "MISSING_OPENING_WIDTH" in exc_codes
    assert "MISSING_OPENING_HEIGHT" in exc_codes


# --------------------------------------------------------------------------
# 3. ROOM TEXT CLASSIFICATION & AMBIGUITY HANDLING
# --------------------------------------------------------------------------

def test_numerical_dimension_rejected_as_room_name():
    """When a polygon contains '3000' and 'MEETING ROOM', room is named 'MEETING ROOM'."""
    solver = RoomBoundarySolver()
    walls = [
        Segment2D(start=Point2D(0, 0), end=Point2D(4000, 0)),
        Segment2D(start=Point2D(4000, 0), end=Point2D(4000, 3000)),
        Segment2D(start=Point2D(4000, 3000), end=Point2D(0, 3000)),
        Segment2D(start=Point2D(0, 3000), end=Point2D(0, 0))
    ]
    texts = [
        ExtractedText(content="3000", location=Point2D(2000, 500), height_mm=150),
        ExtractedText(content="MEETING ROOM", location=Point2D(2000, 1500), height_mm=250),
        ExtractedText(content="4000", location=Point2D(2000, 2500), height_mm=150)
    ]
    rooms = solver.solve_rooms(walls, texts)
    assert len(rooms) == 1
    assert rooms[0].name == "MEETING ROOM", f"Expected 'MEETING ROOM', got '{rooms[0].name}'"


def test_only_numerical_text_produces_unlabeled_room():
    """When a polygon contains only dimension '3000', it must NOT be named '3000'."""
    solver = RoomBoundarySolver()
    walls = [
        Segment2D(start=Point2D(0, 0), end=Point2D(4000, 0)),
        Segment2D(start=Point2D(4000, 0), end=Point2D(4000, 3000)),
        Segment2D(start=Point2D(4000, 3000), end=Point2D(0, 3000)),
        Segment2D(start=Point2D(0, 3000), end=Point2D(0, 0))
    ]
    texts = [
        ExtractedText(content="3000", location=Point2D(2000, 1500), height_mm=150)
    ]
    rooms = solver.solve_rooms(walls, texts)
    assert len(rooms) == 1
    assert "3000" not in rooms[0].name
    assert "Unlabeled" in rooms[0].name
    assert rooms[0].status == EntityStatus.REVIEW_REQUIRED


def test_ambiguous_room_labels_flags_exception():
    """When a polygon contains two valid room labels, AMBIGUOUS_ROOM_LABEL is raised."""
    solver = RoomBoundarySolver()
    walls = [
        Segment2D(start=Point2D(0, 0), end=Point2D(6000, 0)),
        Segment2D(start=Point2D(6000, 0), end=Point2D(6000, 4000)),
        Segment2D(start=Point2D(6000, 4000), end=Point2D(0, 4000)),
        Segment2D(start=Point2D(0, 4000), end=Point2D(0, 0))
    ]
    texts = [
        ExtractedText(content="BOARD ROOM", location=Point2D(2000, 2000), height_mm=250),
        ExtractedText(content="TRAINING ROOM", location=Point2D(4000, 2000), height_mm=250)
    ]
    rooms = solver.solve_rooms(walls, texts)
    assert len(rooms) == 1
    assert rooms[0].status == EntityStatus.REVIEW_REQUIRED
    assert any(e["code"] == "AMBIGUOUS_ROOM_LABEL" for e in solver.exceptions)


# --------------------------------------------------------------------------
# 4. FINISH MATERIAL FABRICATION ELIMINATION
# --------------------------------------------------------------------------

def test_unassigned_room_produces_raw_area_and_unknown_finish_exception():
    """A room with no finish code and no profile mapping must NOT fabricate 'Vitrified Tile'."""
    room = Room(
        id="R-UNKNOWN-01",
        name="UNSPECIFIED STUDIO",
        polygon=Polygon2D([Point2D(0,0), Point2D(5000,0), Point2D(5000,5000), Point2D(0,5000)]),
        finish_code=None
    )
    rule_engine = QSRuleEngine()
    takeoff = rule_engine.calculate_takeoff("DRW-01", "A-01", "01", [room])

    totals = takeoff.total_by_item()
    # Must NOT contain FL-01 (Vitrified Tile)
    assert "FL-01" not in totals
    # Must contain FL-RAW
    assert "FL-RAW" in totals
    assert totals["FL-RAW"]["total_quantity"] == 25.0
    assert "Unassigned Finish" in totals["FL-RAW"]["description"]

    # Must log UNKNOWN_FLOOR_FINISH and UNKNOWN_CEILING_FINISH
    exc_codes = [e["code"] for e in takeoff.exceptions]
    assert "UNKNOWN_FLOOR_FINISH" in exc_codes
    assert "UNKNOWN_CEILING_FINISH" in exc_codes


def test_room_with_finish_code_assigns_correct_material():
    """When a room has finish_code='VT-01', it maps to FL-01 Vitrified Tile Flooring."""
    room = Room(
        id="R-01",
        name="PRIVATE ROOM",
        polygon=Polygon2D([Point2D(0,0), Point2D(5000,0), Point2D(5000,5000), Point2D(0,5000)]),
        finish_code="VT-01"
    )
    rule_engine = QSRuleEngine()
    takeoff = rule_engine.calculate_takeoff("DRW-01", "A-01", "01", [room])

    totals = takeoff.total_by_item()
    assert "FL-01" in totals
    assert totals["FL-01"]["total_quantity"] == 25.0


def test_yaml_profiles_genuinely_control_calculations():
    """Prove that standard_interior.yaml and commercial_fitout.yaml produce genuinely different items."""
    from pathlib import Path
    profiles_dir = Path(__file__).parent.parent.parent / "qs" / "profiles"
    std_engine = QSRuleEngine(profile_path=profiles_dir / "standard_interior.yaml")
    comm_engine = QSRuleEngine(profile_path=profiles_dir / "commercial_fitout.yaml")

    room = Room(
        id="R-01",
        name="DIRECTOR OFFICE",
        polygon=Polygon2D([Point2D(0,0), Point2D(6000,0), Point2D(6000,4000), Point2D(0,4000)]),
        finish_code="CP-01"  # Carpet code
    )

    std_takeoff = std_engine.calculate_takeoff("DRW-01", "A-01", "01", [room])
    comm_takeoff = comm_engine.calculate_takeoff("DRW-01", "A-01", "01", [room])

    std_totals = std_takeoff.total_by_item()
    comm_totals = comm_takeoff.total_by_item()

    # In standard_interior.yaml, CP-01 maps to FL-01 (Vitrified Tile / Carpet Flooring)
    assert "FL-01" in std_totals
    assert "FL-02" not in std_totals

    # In commercial_fitout.yaml, CP-01 maps to FL-02 (Modular Carpet Tiles)
    assert "FL-02" in comm_totals
    assert "FL-01" not in comm_totals
    assert "Carpet Tiles" in comm_totals["FL-02"]["description"]


def test_line_item_audit_lineage_and_deductions():
    """Verify that every quantity stores rule_id, rule_version, measurement_method, formula, and deductions."""
    from core.models.semantics import OpeningType
    room = Room(
        id="R-01",
        name="MEETING ROOM",
        polygon=Polygon2D([Point2D(0,0), Point2D(4000,0), Point2D(4000,3000), Point2D(0,3000)]),
        finish_code="VT-01",
        skirting_finish_code="SK-01"
    )
    door = Opening(
        id="DR-001",
        opening_type=OpeningType.DOOR,
        location=Point2D(2000, 0),
        width_m=0.90,
        height_m=2.10,
        confidence=0.98,
        jamb_p1=Point2D(1550, 0),
        jamb_p2=Point2D(2450, 0)
    )

    rule_engine = QSRuleEngine()
    takeoff = rule_engine.calculate_takeoff("DRW-01", "A-01", "01", [room], openings=[door])

    assert len(takeoff.items) >= 3  # Flooring, Skirting, Ceiling, Door
    for item in takeoff.items:
        assert item.rule_id is not None and len(item.rule_id) > 0
        assert item.rule_version == "1.0.0"
        assert item.measurement_method.startswith("IS 1200")
        assert item.formula is not None and len(item.formula) > 0
        assert isinstance(item.deductions, list)
        assert isinstance(item.source_entities, list) and len(item.source_entities) > 0

    # Specifically check skirting item deductions
    sk_item = next(it for it in takeoff.items if it.item_code == "SK-01")
    assert len(sk_item.deductions) == 1
    assert sk_item.deductions[0]["type"] == "DOOR_OPENING"
    assert sk_item.deductions[0]["source_entity"] == "DR-001"
    assert sk_item.deductions[0]["deduction_value"] == 0.90

