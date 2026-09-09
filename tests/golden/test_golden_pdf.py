"""
Golden Vector PDF Regression Test
Validates end-to-end PDF classification -> Scale calibration -> Primitive extraction -> Room solving -> QS takeoff.
Enforces Blueprint Section 4 (Vector PDF) & Section 98 (Phase 2 Acceptance Criteria).
"""

import pytest
from pathlib import Path
from tests.fixtures.synthetic_pdf import create_synthetic_vector_pdf
from parsers.classifier import DrawingTypeClassifier, DrawingType
from parsers.pdf_vector.extractor import VectorPDFExtractor
from semantics.rooms.boundary_solver import RoomBoundarySolver
from qs.rule_engine import QSRuleEngine

def test_golden_synthetic_vector_pdf_takeoff(tmp_path: Path):
    # 1. Generate known benchmark Vector PDF
    pdf_file = tmp_path / "golden_office_plan.pdf"
    create_synthetic_vector_pdf(pdf_file)

    # 2. Test Drawing Type Classifier
    classification = DrawingTypeClassifier.classify_file(pdf_file)
    assert classification.overall_type == DrawingType.VECTOR_PDF
    assert classification.page_count == 1
    assert classification.pages[0].vector_path_count > 0
    assert classification.pages[0].char_count > 0

    # 3. Extract Primitives with Scale Calibration
    extractor = VectorPDFExtractor()
    parsed_pdf = extractor.extract_page(pdf_file, page_number=1)

    # Assert scale discovery
    assert parsed_pdf.scale.ratio_string == "1:100"
    assert parsed_pdf.scale.source == "explicit_scale_note"
    assert len(parsed_pdf.segments) > 0
    assert len(parsed_pdf.texts) > 0

    # 4. Solve Room Boundaries from Extracted Vector Segments
    solver = RoomBoundarySolver()
    rooms = solver.solve_rooms(parsed_pdf.segments, parsed_pdf.texts)

    # Must detect exactly 2 rooms
    assert len(rooms) == 2
    room_names = [r.name for r in rooms]
    assert any("CONFERENCE" in name for name in room_names)
    assert any("EXECUTIVE" in name for name in room_names)

    conf_room = next(r for r in rooms if "CONFERENCE" in r.name)
    cabin_room = next(r for r in rooms if "EXECUTIVE" in r.name)

    # Mathematical area verification:
    # Conference Room: 6m x 4m = 24.0 sqm
    assert pytest.approx(conf_room.net_area_sqm, abs=0.1) == 24.0
    # Executive Cabin: 4m x 4m = 16.0 sqm
    assert pytest.approx(cabin_room.net_area_sqm, abs=0.1) == 16.0

    # 5. Run QS Rule Engine
    rule_engine = QSRuleEngine()
    takeoff = rule_engine.calculate_takeoff(
        drawing_id="DRW-PDF-001",
        drawing_number="A-101",
        revision="02",
        rooms=rooms
    )

    totals = takeoff.total_by_item()
    # Total flooring = 24 + 16 = 40.0 sqm
    assert pytest.approx(totals["FL-01"]["total_quantity"], abs=0.1) == 40.0
    assert totals["FL-01"]["unit"] == "sqm"
