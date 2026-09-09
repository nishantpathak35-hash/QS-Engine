"""
True Real-Drawing Golden Benchmark Test Suite
Validates all 10 anonymized CAD/PDF interior drawings against verified manual QS measurement sheets.
Enforces Blueprint Section 98 & Audit Findings 11, 12, 13:
- Opens file -> Parses -> Detects geometry -> Builds semantics -> Executes QS -> Compares with verified measurement
- Does NOT reconstruct geometry in Python.
"""

from pathlib import Path
import yaml
import pytest

from parsers.dxf.reader import DXFParser
from parsers.dxf.layer_classifier import LayerCategory
from parsers.pdf_vector.extractor import VectorPDFExtractor
from semantics.rooms.boundary_solver import RoomBoundarySolver
from semantics.openings.door_detector import DoorDetector
from qs.rule_engine import QSRuleEngine
from core.models.project_profile import ProjectProfile

GOLDEN_DIR = Path(__file__).parent
MANIFEST_PATH = GOLDEN_DIR / "verified_measurements.yaml"

with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
    BENCHMARK_DATA = yaml.safe_load(f)["drawings"]


@pytest.mark.parametrize("filename,verified_data", list(BENCHMARK_DATA.items()))
def test_real_drawing_benchmark_file(filename: str, verified_data: dict):
    """Executes true file-based parsing, geometry detection, semantic solver, and QS takeoff."""
    file_path = GOLDEN_DIR / filename
    assert file_path.exists(), f"Benchmark file {filename} not found!"

    verified = verified_data["verified"]
    file_fmt = verified_data["format"]

    rule_engine = QSRuleEngine()
    solver = RoomBoundarySolver()
    has_commercial_finishes = any("FL-02" in k for k in verified.get("flooring", {})) or any("SK-02" in k for k in verified.get("skirting", {}))
    active_profile = "commercial_fitout.yaml" if has_commercial_finishes else "standard_interior.yaml"
    profile = ProjectProfile(
        project_id=f"BENCHMARK-{filename}",
        units="mm",
        active_rule_profile=active_profile,
        allow_assumptions=False,
        room_finish_mapping_enabled=False
    )

    if file_fmt == "DXF":
        # 1. Parse DXF geometry
        parser = DXFParser()
        parsed_dxf = parser.parse_file(file_path)
        assert parsed_dxf.scale_to_mm == 1.0

        # 2. Extract walls and detect doors
        wall_segments = parsed_dxf.get_segments_by_category(LayerCategory.WALL, parser.layer_profile)
        door_detector = DoorDetector()
        openings, non_door_blocks, _ = door_detector.process_blocks(parsed_dxf.blocks, wall_segments)

        # 3. Solve room topology
        rooms = solver.solve_rooms(wall_segments, parsed_dxf.texts, door_openings=openings)
        assert len(rooms) == len(verified["rooms"]), f"{filename}: Room count mismatch! Found {len(rooms)}, expected {len(verified['rooms'])}"

        # 4. Execute QS Rule Engine
        takeoff = rule_engine.calculate_takeoff(
            drawing_id=filename,
            drawing_number=filename,
            revision="01",
            rooms=rooms,
            openings=openings,
            project_profile=profile
        )

        # 5. Verify room-level measurements
        for room in rooms:
            clean_name = room.name.strip().upper()
            assert clean_name in verified["rooms"], f"Unexpected room: {clean_name} in {filename}"
            expected_room = verified["rooms"][clean_name]
            assert pytest.approx(room.net_area_sqm, abs=0.05) == expected_room["area_sqm"]
            assert pytest.approx(room.gross_perimeter_m, abs=0.1) == expected_room["perimeter_m"]

        # 6. Verify door counts
        expected_doors = verified["doors"]["total"]
        assert len(openings) == expected_doors, f"{filename}: Door count {len(openings)} != expected {expected_doors}"

        # 7. Verify flooring totals
        totals = takeoff.total_by_item()
        for item_code, expected_qty in verified.get("flooring", {}).items():
            assert item_code in totals, f"Missing {item_code} flooring in {filename}"
            assert pytest.approx(totals[item_code]["total_quantity"], abs=0.2) == expected_qty

    elif file_fmt == "PDF":
        # 1. Extract PDF geometry with Scale Calibration
        extractor = VectorPDFExtractor(user_scale_ratio=100)
        parsed_pdf = extractor.extract_page(file_path, page_number=1)

        # 2. Wall detection and Room topology
        wall_candidates = parsed_pdf.get_wall_candidates(wall_detector=extractor.wall_detector)
        rooms = solver.solve_rooms(wall_candidates, parsed_pdf.texts)
        assert len(rooms) == len(verified["rooms"]), f"{filename}: Room count mismatch! Found {len(rooms)}, expected {len(verified['rooms'])}"

        # 3. Execute QS Rule Engine
        takeoff = rule_engine.calculate_takeoff(
            drawing_id=filename,
            drawing_number=filename,
            revision="01",
            rooms=rooms,
            project_profile=profile
        )

        # 4. Verify room-level measurements
        for room in rooms:
            clean_name = room.name.strip().upper()
            matching_key = next((k for k in verified["rooms"] if k in clean_name or clean_name in k), None)
            assert matching_key is not None, f"Unexpected room {clean_name} in {filename}"
            expected_room = verified["rooms"][matching_key]
            assert pytest.approx(room.net_area_sqm, abs=0.2) == expected_room["area_sqm"]

        # 5. Verify flooring totals
        totals = takeoff.total_by_item()
        for item_code, expected_qty in verified.get("flooring", {}).items():
            assert item_code in totals, f"Missing {item_code} flooring in {filename}"
            assert pytest.approx(totals[item_code]["total_quantity"], abs=0.5) == expected_qty
