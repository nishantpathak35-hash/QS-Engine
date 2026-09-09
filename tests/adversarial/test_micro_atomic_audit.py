"""
Adversarial Test Suite — Micro-Atomic Fit-Out Audit Verification
Tests all precision edge-cases discovered during deep audit:
1. Fast-path base_measurements reconciliation (door count, workstations, sqft, rft).
2. /quantities endpoint base_measurements persistence.
3. Cost engine floor area dynamic fallback when base_measurements floor area is missing.
4. Excel exporter executive benchmark rows (Rate/sqft and Rate/sqm in Sheet 3).
"""

import pytest
from fastapi.testclient import TestClient
import openpyxl

from apps.api.main import app, TAKEOFF_DB
from vision.ai_drawing_agent import AIDrawingAgent
from qs.rule_engine import QSRuleEngine
from pricing.cost_engine import CostEstimationEngine, FitoutGrade
from exports.exporter import QSExporter
from core.models.takeoff import TakeoffSummary, TakeoffLineItem
from core.units import DisplayUnit
from core.models.semantics import Room, EntityStatus

client = TestClient(app)


def test_base_measurements_fitout_metrics():
    """Verify base_measurements contains sqft, rft, and accurate door count."""
    from core.geometry.primitives import Point2D, Polygon2D
    poly = Polygon2D(vertices=[Point2D(0, 0), Point2D(10000, 0), Point2D(10000, 10000), Point2D(0, 10000)]) # 100 sqm, 40m perim
    room = Room(id="R1", name="Office", polygon=poly, confidence=1.0, status=EntityStatus.AUTO_MEASURED, drawing_id="DWG-01")
    rule_engine = QSRuleEngine()
    takeoff = rule_engine.calculate_takeoff("TEST-DWG", "DWG-01", "0", [room], [], [])

    bm = takeoff.base_measurements
    assert "total_floor_area_sqm" in bm
    assert "total_floor_area_sqft" in bm
    assert "total_room_perimeter_m" in bm
    assert "total_room_perimeter_rft" in bm
    assert bm["total_floor_area_sqm"] == 100.0
    assert bm["total_floor_area_sqft"] == 1076.39
    assert bm["total_room_perimeter_m"] == 40.0
    assert bm["total_room_perimeter_rft"] == 131.23



def test_cost_engine_fallback_flooring_sum():
    """Verify cost engine dynamically sums flooring items when base_measurements floor area is 0 or 1.0."""
    takeoff = TakeoffSummary(
        drawing_id="FALLBACK-DWG",
        drawing_number="DWG-FB",
        revision="01",
        items=[
            TakeoffLineItem(
                id="T1", item_code="FL-02", description="Carpet Tile", location="Office",
                quantity=200.0, unit=DisplayUnit.SQM, formula="200", source_entities=[],
                confidence=1.0, status=EntityStatus.AUTO_MEASURED, rule_id="R1",
                rule_version="1.0", calculator="c", measurement_method="m"
            ),
            TakeoffLineItem(
                id="T2", item_code="FL-01", description="Vitrified Tile", location="Lobby",
                quantity=100.0, unit=DisplayUnit.SQM, formula="100", source_entities=[],
                confidence=1.0, status=EntityStatus.AUTO_MEASURED, rule_id="R2",
                rule_version="1.0", calculator="c", measurement_method="m"
            )
        ],
        base_measurements={"total_floor_area_sqm": 0.0} # Missing or zero area
    )

    estimate = CostEstimationEngine.estimate_project_cost(takeoff, fitout_grade=FitoutGrade.STANDARD)
    # Total area should fall back to 300.0 sqm (not 1.0 m!)
    assert estimate.cost_per_sqm_inr < estimate.grand_total_budget_inr / 100.0
    expected_sqm_cost = estimate.grand_total_budget_inr / 300.0
    assert abs(estimate.cost_per_sqm_inr - expected_sqm_cost) < 0.1
    expected_sqft_cost = expected_sqm_cost / 10.7639104
    assert abs(estimate.cost_per_sqft_inr - expected_sqft_cost) < 0.1


def test_quantities_endpoint_returns_base_measurements():
    """Verify /v1/drawings/{id}/quantities returns base_measurements."""
    takeoff = TakeoffSummary(
        drawing_id="API-TEST-DWG",
        drawing_number="DWG-API",
        revision="01",
        items=[],
        base_measurements={
            "total_room_count": 5,
            "total_floor_area_sqm": 150.0,
            "total_floor_area_sqft": 1614.59,
            "total_door_count": 6
        }
    )
    TAKEOFF_DB["API-TEST-DWG"] = takeoff

    res = client.get("/v1/drawings/API-TEST-DWG/quantities")
    assert res.status_code == 200
    data = res.json()
    assert "base_measurements" in data
    assert data["base_measurements"]["total_door_count"] == 6
    assert data["base_measurements"]["total_floor_area_sqft"] == 1614.59


def test_excel_export_has_executive_kpis(tmp_path):
    """Verify Sheet 3 has Fit-out Rate / SQFT and Fit-out Rate / SQM."""
    takeoff = TakeoffSummary(
        drawing_id="EXPORT-KPI-DWG",
        drawing_number="DWG-KPI",
        revision="01",
        items=[
            TakeoffLineItem(
                id="TK-1", item_code="FL-02", description="Modular Carpet Tile", location="Open Office",
                quantity=500.0, unit=DisplayUnit.SQM, formula="500", source_entities=[],
                confidence=1.0, status=EntityStatus.AUTO_MEASURED, rule_id="R1",
                rule_version="1.0", calculator="c", measurement_method="m"
            )
        ],
        base_measurements={"total_floor_area_sqm": 500.0}
    )

    out_xlsx = tmp_path / "kpi_export.xlsx"
    QSExporter.export_excel(takeoff, out_xlsx)

    wb = openpyxl.load_workbook(out_xlsx, data_only=False)
    ws3 = wb["Priced BOQ & Budget"]

    labels = [ws3.cell(row=r, column=11).value for r in range(1, ws3.max_row + 1)]
    assert any("Fit-out Rate / SQFT" in str(l) for l in labels)
    assert any("Fit-out Rate / SQM" in str(l) for l in labels)


def test_csv_export_string_unit_and_status_safety():
    """Verify export_csv does not crash when item.unit or item.status is a plain string instead of an Enum."""
    takeoff = TakeoffSummary(
        drawing_id="CSV-STR-DWG",
        drawing_number="DWG-CSV",
        revision="01",
        items=[
            TakeoffLineItem(
                id="CSV-1",
                item_code="FN-01",
                description="Linear Workstation",
                location="Hall",
                quantity=46.0,
                unit="nos",  # plain string
                formula="46 Nos",
                source_entities=[],
                confidence=0.95,
                status="verified",  # plain string
                rule_id="R-STR",
                rule_version="1.0",
                calculator="c",
                measurement_method="m"
            )
        ],
        base_measurements={"total_floor_area_sqm": 200.0}
    )

    csv_out = QSExporter.export_csv(takeoff)
    assert "FN-01" in csv_out
    assert "Linear Workstation" in csv_out
    assert "nos" in csv_out
    assert "verified" in csv_out


def test_trade_categorization_ceiling_tile_and_prefix_priority():
    """Verify Ceiling tiles are categorized under Ceiling & Soffits, NOT Flooring & Tiling."""
    from pricing.cost_engine import CostEstimationEngine

    cat1 = CostEstimationEngine._categorize_trade("CL-02", "Acoustic Mineral Fiber Ceiling Tile 600x600")
    assert cat1 == "Ceiling & Soffits"

    cat2 = CostEstimationEngine._categorize_trade("UNLISTED-CEIL", "Gypsum Board False Ceiling with Soffit Drop")
    assert cat2 == "Ceiling & Soffits"

    cat3 = CostEstimationEngine._categorize_trade("FL-01", "Vitrified Ceramic Floor Tile 1200x600")
    assert cat3 == "Flooring & Tiling"

    cat4 = CostEstimationEngine._categorize_trade("PT-01", "Full Height Gypsum Board Drywall Partition")
    assert cat4 == "Partitions & Drywalls"

    cat5 = CostEstimationEngine._categorize_trade("GL-01", "Toughened Acoustic Glass Partition")
    assert cat5 == "Glazing & Acoustic Partitions"

    cat6 = CostEstimationEngine._categorize_trade("AV-01", "85-inch 4K Commercial Presentation Display TV")
    assert cat6 == "AV & IT Infrastructure"

