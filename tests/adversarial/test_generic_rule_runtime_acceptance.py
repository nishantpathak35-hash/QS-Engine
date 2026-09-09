"""
Acceptance Test for Generic Rule Runtime (Requirement 17).
Verifies:
- The rule engine knows nothing about trade-specific hardcodings in Python.
- Adding a brand-new YAML rule with 'item_code: DEMO-001', 'source_entity: room',
  'calculator: generic.polygon_area', 'unit: sqm' executes purely via configuration.
- Adding a brand-new YAML rule with 'item_code: DEMO-002', 'source_entity: wall',
  'calculator: generic.linear_length', 'unit: rm' executes purely via configuration.
- Zero Python code changes required.
"""

from pathlib import Path
import pytest
import yaml

from core.geometry.primitives import Point2D, Polygon2D, Segment2D
from core.models.semantics import Room, WallSegment
from core.models.project_profile import ProjectProfile
from qs.rule_engine import QSRuleEngine


def test_generic_rule_runtime_zero_python_change(tmp_path: Path):
    """Proves the rule engine is completely generic and executes new trade YAML without code changes."""
    # 1. Author a completely novel YAML profile with two brand new demo items
    custom_profile_dict = {
        "profile_id": "CUSTOM_NOVEL_TRADE_PROFILE",
        "profile_version": "1.0.0",
        "standard": "IS 1200 / Generic Metric",
        "rules": [
            {
                "rule_id": "QS-DEMO-001",
                "item_code": "DEMO-001",
                "category": "novel_trade",
                "description": "Novel Acoustic Room Ceiling Panel Area",
                "unit": "sqm",
                "source_entity": "room",
                "calculator": "generic.polygon_area",
                "match_policy": "exclusive",
                "applies_when": {
                    "room_type": "STUDIO"
                }
            },
            {
                "rule_id": "QS-DEMO-002",
                "item_code": "DEMO-002",
                "category": "novel_linear_trade",
                "description": "Novel Perimeter Floor Trench Linear Measure",
                "unit": "rm",
                "source_entity": "wall",
                "calculator": "generic.linear_length",
                "match_policy": "exclusive",
                "applies_when": {
                    "wall_type": "trench"
                }
            }
        ]
    }

    profile_file = tmp_path / "novel_trade.yaml"
    with open(profile_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(custom_profile_dict, f)

    # 2. Instantiate generic rule engine targeting this new profile
    engine = QSRuleEngine(profile_path=profile_file)

    # 3. Create synthetic Room and Wall entities
    test_room = Room(
        id="R-999",
        name="AUDIO STUDIO",
        polygon=Polygon2D(vertices=[
            Point2D(0, 0), Point2D(5000, 0), Point2D(5000, 4000), Point2D(0, 4000)
        ]),  # 5m x 4m = 20.0 sqm
        confidence=0.95
    )

    test_wall = WallSegment(
        id="WALL-999",
        start=Point2D(0, 0),
        end=Point2D(7500, 0),  # 7.5 m
        thickness_mm=100.0,
        wall_type="trench",
        confidence=0.90
    )

    project_profile = ProjectProfile(
        project_id="NOVEL_PROJECT",
        allow_assumptions=False
    )

    # 4. Calculate takeoff
    takeoff = engine.calculate_takeoff(
        drawing_id="DRAW-NOVEL-01",
        drawing_number="NOV-01",
        revision="01",
        rooms=[test_room],
        walls=[test_wall],
        project_profile=project_profile
    )

    # 5. Assert DEMO-001 was calculated for Room
    demo1_items = [it for it in takeoff.items if it.item_code == "DEMO-001"]
    assert len(demo1_items) == 1, "DEMO-001 room rule must execute via generic engine"
    assert pytest.approx(demo1_items[0].quantity, abs=0.01) == 20.00
    assert demo1_items[0].unit.value == "sqm"
    assert demo1_items[0].calculator == "generic.polygon_area"

    # 6. Assert DEMO-002 was calculated for Wall
    demo2_items = [it for it in takeoff.items if it.item_code == "DEMO-002"]
    assert len(demo2_items) == 1, "DEMO-002 wall rule must execute via generic engine"
    assert pytest.approx(demo2_items[0].quantity, abs=0.01) == 7.50
    assert demo2_items[0].unit.value in ("rm", "m")
    assert demo2_items[0].calculator == "generic.linear_length"
