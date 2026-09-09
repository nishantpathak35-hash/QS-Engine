"""
QS Quantification Engine — Physical Vector Fixture & Symbol Detector Unit Tests
Validates fixture detection from CAD DXF and Vector PDF, spatial room attribution,
BOQ line item generation with audit trails, and discrepancy variance audits.
"""

from pathlib import Path
import pytest
from core.geometry.primitives import Point2D, Polygon2D
from core.models.semantics import Room, EntityStatus
from core.models.takeoff import TakeoffLineItem
from core.units import DisplayUnit
from parsers.dxf.reader import ExtractedBlock
from semantics.symbols.physical_fixture_detector import PhysicalFixtureDetector, PhysicalFixture


def test_dxf_physical_fixture_detection_and_spatial_room_assignment():
    """Verifies that DXF lighting and workstation blocks are accurately classified and assigned to enclosing rooms."""
    # Create two test rooms: Conference Room and Main Office
    conf_poly = Polygon2D(vertices=[Point2D(0, 0), Point2D(5000, 0), Point2D(5000, 5000), Point2D(0, 5000)], holes=[])
    office_poly = Polygon2D(vertices=[Point2D(6000, 0), Point2D(12000, 0), Point2D(12000, 6000), Point2D(6000, 6000)], holes=[])

    room_conf = Room(id="RM-01", name="CONFERENCE ROOM", polygon=conf_poly, label_point=Point2D(2500, 2500))
    room_office = Room(id="RM-02", name="OPEN OFFICE", polygon=office_poly, label_point=Point2D(9000, 3000))
    rooms = [room_conf, room_office]

    # Mock DXF drawing with blocks
    class DummyDXF:
        def __init__(self):
            self.blocks = [
                # Downlight inside Conference Room
                ExtractedBlock(name="DOWNLIGHT_6IN", location=Point2D(2500, 2500), rotation_deg=0.0, layer="E-LGT", handle="H1"),
                # Linear Light inside Conference Room
                ExtractedBlock(name="LINEAR_LIGHT_5FT", location=Point2D(2500, 4000), rotation_deg=0.0, layer="E-LGT", handle="H2"),
                # Workstations inside Open Office
                ExtractedBlock(name="WORKSTATION_POD_4", location=Point2D(8000, 2500), rotation_deg=0.0, layer="F-FURN", handle="H3"),
                ExtractedBlock(name="WORKSTATION_POD_4", location=Point2D(10000, 2500), rotation_deg=0.0, layer="F-FURN", handle="H4"),
                # Fixture in unassigned space (outside any room)
                ExtractedBlock(name="CORRIDOR_DOWNLIGHT", location=Point2D(5500, 2500), rotation_deg=0.0, layer="E-LGT", handle="H5"),
            ]

    fixtures = PhysicalFixtureDetector.detect_fixtures_from_dxf(DummyDXF(), rooms=rooms)
    assert len(fixtures) == 5

    # Check spatial assignments
    downlight_conf = next(f for f in fixtures if f.location_point.x == 2500 and f.location_point.y == 2500)
    assert downlight_conf.room_id == "RM-01"
    assert downlight_conf.room_name == "CONFERENCE ROOM"
    assert downlight_conf.item_code == "LT-05"

    linear_conf = next(f for f in fixtures if f.location_point.x == 2500 and f.location_point.y == 4000)
    assert linear_conf.room_id == "RM-01"
    assert linear_conf.item_code == "LT-02"

    ws_1 = next(f for f in fixtures if f.location_point.x == 8000)
    assert ws_1.room_id == "RM-02"
    assert ws_1.item_code == "FN-01"

    outside_fixture = next(f for f in fixtures if f.location_point.x == 5500)
    assert outside_fixture.room_id is None
    assert outside_fixture.room_name is None


def test_takeoff_line_items_generation_with_legend_audit():
    """Verifies that physical fixtures generate auditable BOQ lines with variance tracking."""
    fixtures = [
        PhysicalFixture(
            id="PHYS-LT-05-001",
            fixture_type="concealed_downlight_6in",
            item_code="LT-05",
            description='CONCEALED LIGHT - 6" DIA',
            category="Electrical & Lighting",
            location_point=Point2D(1000, 1000),
            room_name="LOBBY"
        ),
        PhysicalFixture(
            id="PHYS-LT-05-002",
            fixture_type="concealed_downlight_6in",
            item_code="LT-05",
            description='CONCEALED LIGHT - 6" DIA',
            category="Electrical & Lighting",
            location_point=Point2D(2000, 1000),
            room_name="LOBBY"
        )
    ]

    # Legend specifies 3 (variance: plan=2, legend=3 -> difference -1)
    legend_items = [
        TakeoffLineItem(
            id="LEG-LT-05",
            item_code="LT-05",
            description='CONCEALED LIGHT - 6" DIA',
            location="Schedule Legend",
            quantity=3.0,
            unit=DisplayUnit.NOS,
            formula="Legend Text"
        )
    ]

    class MockProfile:
        def get_wastage_percent(self, code, desc):
            return 0.10  # 10% spare wastage

    line_items = PhysicalFixtureDetector.generate_takeoff_line_items(
        fixtures,
        legend_items=legend_items,
        project_profile=MockProfile()
    )

    assert len(line_items) == 1
    lt_item = line_items[0]
    assert lt_item.item_code == "LT-05"
    assert lt_item.quantity == 2.0
    # math.ceil(2 * 1.10) = 3.0 gross quantity
    assert lt_item.gross_quantity == 3.0
    assert "AUDIT VARIANCE vs Legend" in lt_item.formula
    assert "Plan=2, Legend=3" in lt_item.formula
    assert len(lt_item.source_entities) == 2


def test_empty_and_graceful_handling():
    """Verifies that detector returns empty lists on non-existent files or empty inputs without exceptions."""
    assert PhysicalFixtureDetector.detect_fixtures_from_pdf("non_existent_file.pdf") == []
    assert PhysicalFixtureDetector.detect_fixtures_from_dxf(None) == []
    assert PhysicalFixtureDetector.generate_takeoff_line_items([]) == []
