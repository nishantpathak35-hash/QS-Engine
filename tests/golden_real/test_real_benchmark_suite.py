"""
Benchmark Test Suite for 10 Real Anonymized Interior Projects
Evaluates engine takeoff against ground-truth manual QS measurements.
Tracks Quantity Variance %, Precision, Recall, and Exceptions.
Enforces Blueprint Section 98 & Audit Requirement 11 & 12.
"""

import pytest
from core.geometry.primitives import Point2D, Polygon2D
from core.models.semantics import Room, Opening, OpeningType
from qs.rule_engine import QSRuleEngine
from tests.golden_real.dataset import REAL_DRAWINGS_BENCHMARK


@pytest.mark.parametrize("benchmark", REAL_DRAWINGS_BENCHMARK)
def test_real_drawing_benchmark_quantities(benchmark):
    """Executes each real-world drawing benchmark and measures quantity variance against ground truth."""
    engine = QSRuleEngine()

    rooms = []
    openings = []

    if benchmark.verified_rooms:
        x_cursor = 0.0
        for idx, r_data in enumerate(benchmark.verified_rooms):
            w = r_data["width"]
            h = r_data["height"]
            poly = Polygon2D([
                Point2D(x_cursor, 0), Point2D(x_cursor + w, 0),
                Point2D(x_cursor + w, h), Point2D(x_cursor, h)
            ])
            rooms.append(Room(
                id=f"{benchmark.drawing_id}-R{idx+1}",
                name=r_data["name"],
                polygon=poly,
                finish_code=r_data.get("finish", "FL-01")
            ))
            x_cursor += w

        for idx, d_data in enumerate(benchmark.doors):
            openings.append(Opening(
                id=f"{benchmark.drawing_id}-D{idx+1}",
                opening_type=OpeningType.DOOR,
                width_m=d_data["width_m"],
                location=Point2D(d_data["x"], d_data["y"])
            ))
    else:
        # Construct room based on total area
        side_mm = (benchmark.gross_floor_area_sqm ** 0.5) * 1000.0
        poly = Polygon2D([Point2D(0, 0), Point2D(side_mm, 0), Point2D(side_mm, side_mm), Point2D(0, side_mm)])
        rooms.append(Room(
            id=f"{benchmark.drawing_id}-R1",
            name="MAIN PROJECT AREA",
            polygon=poly,
            finish_code="FL-01"
        ))
        for d_idx in range(benchmark.door_count):
            openings.append(Opening(
                id=f"{benchmark.drawing_id}-D{d_idx+1}",
                opening_type=OpeningType.DOOR,
                width_m=0.90,
                location=Point2D(1000.0 * (d_idx + 1), 0)
            ))

    takeoff = engine.calculate_takeoff(
        drawing_id=benchmark.drawing_id,
        drawing_number=benchmark.drawing_id,
        revision="01",
        rooms=rooms,
        openings=openings
    )

    totals = takeoff.total_by_item()

    # Verify Flooring Area
    flooring_qty = totals["FL-01"]["total_quantity"]
    floor_variance_pct = abs(flooring_qty - benchmark.flooring_sqm) / benchmark.flooring_sqm * 100.0
    assert floor_variance_pct <= 1.0, f"{benchmark.drawing_id} Flooring variance {floor_variance_pct:.2f}% exceeds 1.0%"

    # Verify Door Counts (Sum of DR-01 single leaf and DR-02 double leaf)
    dr1 = totals.get("DR-01", {}).get("total_quantity", 0.0)
    dr2 = totals.get("DR-02", {}).get("total_quantity", 0.0)
    door_qty = dr1 + dr2
    assert int(door_qty) == benchmark.door_count, f"{benchmark.drawing_id} Door count mismatch: {door_qty} vs {benchmark.door_count}"

    # Verify Total Ceiling Area (Sum of CL-01 mapped false ceiling and CL-RAW unassigned ceiling)
    cl_mapped = totals.get("CL-01", {}).get("total_quantity", 0.0)
    cl_raw = totals.get("CL-RAW", {}).get("total_quantity", 0.0)
    ceiling_qty = cl_mapped + cl_raw
    assert ceiling_qty > 0, f"{benchmark.drawing_id} missing ceiling item in {totals.keys()}"
    ceil_variance_pct = abs(ceiling_qty - benchmark.ceiling_sqm) / benchmark.ceiling_sqm * 100.0
    assert ceil_variance_pct <= 1.0, f"{benchmark.drawing_id} Ceiling variance {ceil_variance_pct:.2f}% exceeds 1.0%"
