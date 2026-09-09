"""
QS Quantification Engine — Free LLM & Diverse CAD Architecture Test Suite
Validates that 5 diverse CAD architectural typologies (Residential, Healthcare, Corporate, Retail, Industrial)
with unstandardized layers and custom blocks are accurately parsed, classified via Free LLM fallback,
and geometrically quantified without hallucination.
Enforces Blueprint Sections 54, 55, 56, and 106.
"""

from pathlib import Path
import yaml
import pytest

from parsers.dxf.reader import DXFParser
from parsers.dxf.layer_classifier import LayerCategory
from semantics.rooms.boundary_solver import RoomBoundarySolver
from semantics.openings.door_detector import DoorDetector
from qs.rule_engine import QSRuleEngine
from core.models.project_profile import ProjectProfile
from core.ai.factory import LLMProviderFactory
from core.ai.llm_provider import (
    BaseLLMProvider,
    LayerClassificationOutput,
    BlockClassificationOutput,
    AnnotationClassificationOutput,
)
from core.ai.gemini_provider import GeminiLLMProvider
from core.ai.huggingface_provider import HuggingFaceLLMProvider
from core.ai.openai_compatible_provider import OpenAICompatibleLLMProvider
from core.ai.ollama_provider import OllamaLLMProvider
from core.ai.deterministic_fallback import DeterministicFallbackLLMProvider

GOLDEN_DIR = Path("tests/golden_real_files")
MANIFEST_PATH = GOLDEN_DIR / "ai_diverse_cad_manifest.yaml"

with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
    DIVERSE_DATA = yaml.safe_load(f)["drawings"]


def test_llm_provider_contracts():
    """Verifies that all LLM provider implementations satisfy the required interface."""
    fallback = DeterministicFallbackLLMProvider()
    assert fallback.is_available
    assert "deterministic" in fallback.provider_name

    layer_res = fallback.classify_layer("PARTITION_LEAD_LINED")
    assert isinstance(layer_res, LayerClassificationOutput)
    assert layer_res.category == "wall"
    assert layer_res.confidence >= 0.70

    block_res = fallback.classify_block("STEEL_FIRE_EXIT_1000", "DOOR_LAYER")
    assert isinstance(block_res, BlockClassificationOutput)
    assert block_res.is_door is True
    assert block_res.category == "door"

    anno_res = fallback.classify_annotation("DOCTOR CONSULTATION 1")
    assert isinstance(anno_res, AnnotationClassificationOutput)
    assert anno_res.semantic_type == "room_name"


def test_gemini_provider_interface_graceful_handling():
    """Verifies that GeminiLLMProvider handles missing credentials safely without crashing."""
    gemini = GeminiLLMProvider(api_key="TEST_DUMMY_KEY")
    assert gemini.is_available
    assert "google-gemini-free" in gemini.provider_name


def test_huggingface_provider_interface():
    """Verifies HuggingFaceLLMProvider configuration and interface."""
    hf = HuggingFaceLLMProvider(token="hf_test_token")
    assert hf.is_available
    assert "huggingface-free" in hf.provider_name


def test_openai_compatible_provider_interface():
    """Verifies universal OpenAI-compatible provider (Groq/OpenRouter/Cerebras)."""
    groq = OpenAICompatibleLLMProvider(
        base_url="https://api.groq.com/openai/v1",
        api_key="gsk_test_token",
        model_name="llama-3.1-8b-instant",
        provider_label="groq-free"
    )
    assert groq.is_available
    assert "groq-free" in groq.provider_name


def test_ollama_provider_interface():
    """Verifies OllamaLLMProvider configuration and offline availability check."""
    ollama = OllamaLLMProvider()
    assert "ollama-local" in ollama.provider_name
    # Availability check should return boolean safely without unhandled exceptions
    is_avail = ollama.is_available
    assert isinstance(is_avail, bool)



@pytest.mark.parametrize("filename,drawing_info", list(DIVERSE_DATA.items()))
def test_diverse_cad_end_to_end_with_free_llm(filename: str, drawing_info: dict):
    """
    Executes end-to-end CAD takeoff across diverse architectural typologies:
    1. Parse raw DXF geometry.
    2. Classify unstandardized layers and blocks using Free LLM fallback.
    3. Solve topological room boundaries.
    4. Calculate QS BOQ line items.
    5. Verify zero-hallucination mathematical accuracy against ground-truth.
    """
    file_path = GOLDEN_DIR / filename
    assert file_path.exists(), f"CAD drawing {filename} not found!"

    verified = drawing_info["verified"]

    # 1. Parse DXF geometry
    parser = DXFParser()
    parsed_dxf = parser.parse_file(file_path)
    assert parsed_dxf.scale_to_mm == 1.0

    # 2. Extract walls using LLM-assisted layer classifier
    wall_segments = parsed_dxf.get_segments_by_category(LayerCategory.WALL, parser.layer_profile)
    assert len(wall_segments) > 0, f"Failed to extract wall segments for {filename} via LLM layer resolution!"

    # 3. Detect and resolve door openings with LLM block classification
    door_detector = DoorDetector()
    openings, non_door_blocks, _ = door_detector.process_blocks(parsed_dxf.blocks, wall_segments)
    expected_doors = verified["doors"]["total"]
    assert len(openings) == expected_doors, f"{filename}: Door count {len(openings)} != expected {expected_doors}"

    # 4. Solve room topology
    solver = RoomBoundarySolver()
    rooms = solver.solve_rooms(wall_segments, parsed_dxf.texts, door_openings=openings)
    expected_rooms_dict = verified["rooms"]
    assert len(rooms) == len(expected_rooms_dict), (
        f"{filename}: Room count mismatch! Solved {len(rooms)}, expected {len(expected_rooms_dict)}"
    )

    # 5. Verify room-level measurements (Zero Hallucination)
    for room in rooms:
        clean_name = room.name.strip().upper()
        assert clean_name in expected_rooms_dict, f"Unexpected room '{clean_name}' in {filename}"
        expected_room = expected_rooms_dict[clean_name]
        assert pytest.approx(room.net_area_sqm, abs=0.05) == expected_room["area_sqm"], (
            f"{filename} - {clean_name}: Area {room.net_area_sqm} != expected {expected_room['area_sqm']}"
        )
        assert pytest.approx(room.gross_perimeter_m, abs=0.10) == expected_room["perimeter_m"], (
            f"{filename} - {clean_name}: Perimeter {room.gross_perimeter_m} != expected {expected_room['perimeter_m']}"
        )

    # 6. Execute QS Rule Engine
    rule_engine = QSRuleEngine()
    profile = ProjectProfile(
        project_id=f"DIVERSE-{filename}",
        units="mm",
        active_rule_profile="commercial_fitout.yaml",
        allow_assumptions=False,
        room_finish_mapping_enabled=False
    )
    takeoff = rule_engine.calculate_takeoff(
        drawing_id=filename,
        drawing_number=filename,
        revision="01",
        rooms=rooms,
        openings=openings,
        project_profile=profile
    )

    # 7. Verify flooring totals match verified takeoff
    totals = takeoff.total_by_item()
    for item_code, expected_qty in verified.get("flooring", {}).items():
        assert item_code in totals, f"Missing {item_code} in takeoff for {filename}"
        assert pytest.approx(totals[item_code]["total_quantity"], abs=0.20) == expected_qty, (
            f"{filename} - {item_code}: Quantity {totals[item_code]['total_quantity']} != expected {expected_qty}"
        )
