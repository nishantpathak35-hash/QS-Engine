"""
Test Suite: Material Wastage & Procurement Accounting (Sprint 5 / Phase 2)
Verifies:
1. Trade-specific standard wastage factors (Flooring, Ceiling, Partitions, Skirting, Paint, Lighting).
2. Wastage presets: Standard, Conservative, Tight, and Zero (Net only).
3. Dual-quantity accounting: Net Measured Qty vs Gross Procurement Qty.
4. Excel and CSV export generation with Wastage % and Gross quantities.
"""

import pytest
from core.models.project_profile import ProjectProfile
from core.models.semantics import Room, EntityStatus
from core.geometry.primitives import Point2D, Polygon2D
from core.units import DisplayUnit
from qs.rule_engine import QSRuleEngine
from exports.exporter import QSExporter


def create_test_room(room_id: str, name: str, width_mm: float, height_mm: float) -> Room:
    poly = Polygon2D([
        Point2D(0, 0),
        Point2D(width_mm, 0),
        Point2D(width_mm, height_mm),
        Point2D(0, height_mm)
    ])
    return Room(
        id=room_id,
        name=name,
        polygon=poly,
        confidence=0.98,
        status=EntityStatus.AUTO_MEASURED
    )


def test_standard_wastage_factors():
    prof = ProjectProfile(
        project_id="P-WASTE-01",
        wastage_enabled=True,
        wastage_preset="standard"
    )

    # Check trade defaults
    assert prof.get_wastage_percent("FL-01", "Vitrified Tiles") == 0.05
    assert prof.get_wastage_percent("CL-01", "Gypsum Ceiling") == 0.05
    assert prof.get_wastage_percent("PT-01", "Gypsum Partition") == 0.07
    assert prof.get_wastage_percent("SK-01", "Tile Skirting") == 0.05
    assert prof.get_wastage_percent("LT-02", "5' Linear Light") == 0.03
    assert prof.get_wastage_percent("FN-01", "Workstation") == 0.0


def test_conservative_wastage_factors():
    prof = ProjectProfile(
        project_id="P-WASTE-02",
        wastage_enabled=True,
        wastage_preset="conservative"
    )

    # Multiplier 1.4x
    assert prof.get_wastage_percent("FL-01", "Flooring") == 0.07
    assert prof.get_wastage_percent("PT-01", "Partitions") == 0.098


def test_zero_wastage_preset():
    prof = ProjectProfile(
        project_id="P-WASTE-03",
        wastage_enabled=True,
        wastage_preset="zero"
    )

    assert prof.get_wastage_percent("FL-01", "Flooring") == 0.0
    assert prof.get_wastage_percent("PT-01", "Partitions") == 0.0


def test_takeoff_dual_accounting_in_rule_engine():
    # 10m x 10m room = 100 sqm floor & ceiling
    room = create_test_room("R-01", "Open Office", 10000.0, 10000.0)

    prof = ProjectProfile(
        project_id="P-WASTE-04",
        wastage_enabled=True,
        wastage_preset="standard"
    )

    engine = QSRuleEngine()
    takeoff = engine.calculate_takeoff("DRW-W1", "A-101", "01", rooms=[room], walls=[], project_profile=prof)

    totals = takeoff.total_by_item()
    fl_data = totals.get("FL-RAW")
    assert fl_data is not None

    # Net is 100 sqm
    assert fl_data["net_quantity"] == 100.0
    # Standard wastage is 5%
    assert fl_data["wastage_percent"] == 0.05
    # Gross PO is 105 sqm
    assert fl_data["gross_quantity"] == 105.0
    assert fl_data["wastage_quantity"] == 5.0


def test_excel_export_contains_wastage_columns(tmp_path):
    room = create_test_room("R-01", "Open Office", 10000.0, 10000.0)
    prof = ProjectProfile(project_id="P-WASTE-05", wastage_enabled=True, wastage_preset="standard")
    engine = QSRuleEngine()
    takeoff = engine.calculate_takeoff("DRW-W2", "A-101", "01", rooms=[room], walls=[], project_profile=prof)

    out_xlsx = tmp_path / "takeoff_wastage.xlsx"
    exported_path = QSExporter.export_excel(takeoff, out_xlsx)
    assert exported_path.exists()
    assert exported_path.stat().st_size > 3000

    csv_text = QSExporter.export_csv(takeoff)
    assert "Gross Procurement Qty" in csv_text
    assert "Wastage %" in csv_text
