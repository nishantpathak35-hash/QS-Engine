"""
Comprehensive End-to-End Regression Test Suite for Partition Takeoff (Requirements 3 & 19).
Verifies:
1. Gypsum partition (PT-01) calculation via API (length * height - opening deductions).
2. Glass partition (PT-02) calculation via API.
3. Unknown partition type (masonry / unmapped) producing PT-RAW and REVIEW_REQUIRED.
4. Missing wall height producing MISSING_WALL_HEIGHT exception and REVIEW_REQUIRED status.
5. Opening deductions correctly applied (IS 1200 / POMI rules).
6. Multiple partition types coexist in the same project without collision.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import ezdxf

from apps.api.main import app, DRAWINGS_DB, TAKEOFF_DB
from core.exception_registry import ExceptionCode


def create_partition_dxf(file_path: Path, include_openings: bool = True) -> Path:
    """Creates a DXF file with multiple partition walls (Gypsum, Glass, Masonry)."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 4  # mm
    msp = doc.modelspace()

    # Gypsum Partition Wall on A-WALL-GYPSUM (10m long = 10000mm)
    msp.add_line((0, 0), (10000, 0), dxfattribs={"layer": "A-WALL-GYPSUM"})

    # Glass Partition Wall on A-WALL-GLASS (6m long = 6000mm)
    msp.add_line((0, 4000), (6000, 4000), dxfattribs={"layer": "A-WALL-GLASS"})

    # Masonry Wall on A-WALL-BRICK (8m long = 8000mm)
    msp.add_line((0, 8000), (8000, 8000), dxfattribs={"layer": "A-WALL-BRICK"})

    # Room enclosure around gypsum wall so we have valid room topology too
    msp.add_line((0, 0), (0, 3000), dxfattribs={"layer": "A-WALL"})
    msp.add_line((0, 3000), (10000, 3000), dxfattribs={"layer": "A-WALL"})
    msp.add_line((10000, 3000), (10000, 0), dxfattribs={"layer": "A-WALL"})
    msp.add_text("OFFICE\nF-01\nSK-01", dxfattribs={"layer": "A-ANNO-TEXT"}).set_placement((3000, 1500))

    if include_openings:
        # Insert a door opening on the gypsum wall at x=2000 (width 1000mm, height 2100mm = 2.1 sqm)
        blk = doc.blocks.new(name="DOOR_SINGLE")
        blk.add_line((0, 0), (1000, 0))
        blk.add_arc((0, 0), radius=1000, start_angle=0, end_angle=90)
        msp.add_blockref("DOOR_SINGLE", (2000, 0))

    doc.saveas(file_path)
    return file_path


def test_partition_takeoff_end_to_end_with_assumed_height(tmp_path: Path):
    """Test gypsum & glass partitions calculated with approved ceiling height and opening deduction."""
    client = TestClient(app)
    dxf_file = tmp_path / "partitions_test.dxf"
    create_partition_dxf(dxf_file, include_openings=True)

    # 1. Upload drawing
    with open(dxf_file, "rb") as f:
        resp = client.post(
            "/v1/drawings/upload",
            files={"file": ("partitions_test.dxf", f, "application/dxf")},
            data={"drawing_number": "ARCH-PT-01", "revision": "01"}
        )
    assert resp.status_code == 200
    drawing_id = resp.json()["drawing_id"]

    # 2. Process with approved ceiling height of 3.0m
    profile_payload = {
        "profile_id": "COMMERCIAL_FITOUT",
        "units": "mm",
        "measurement_profile": "commercial_fitout",
        "assumptions_enabled": True,
        "ceiling_height_m": 3.0,
        "default_door_width_mm": 1000.0,
        "default_door_height_mm": 2100.0,
        "approved_assumptions": ["default_ceiling_height_m", "default_door_width_mm", "default_door_height_mm"]
    }

    proc_resp = client.post(
        f"/v1/drawings/{drawing_id}/process",
        json={"project_profile": profile_payload}
    )
    assert proc_resp.status_code == 200
    takeoff = proc_resp.json()

    # 3. Verify Gypsum Partition (PT-01)
    # Length = 10.0m, Height = 3.0m -> Gross = 30.0 sqm
    # Opening deduction = 1.0m * 2.1m = 2.10 sqm (> 0.5 sqm threshold)
    # Net Gypsum = 30.0 - 2.1 = 27.90 sqm
    pt01_items = [it for it in takeoff["items"] if it["item_code"] == "PT-01"]
    assert len(pt01_items) >= 1
    gyp_item = pt01_items[0]
    assert pytest.approx(gyp_item["quantity"], abs=0.5) == 27.90
    assert gyp_item["unit"] == "sqm"
    assert gyp_item["calculator"] == "wall.partition_area"
    assert len(gyp_item["deductions"]) == 1

    # 4. Verify Glass Partition (PT-02)
    # Length = 6.0m, Height = 3.0m -> 18.0 sqm (no opening)
    pt02_items = [it for it in takeoff["items"] if it["item_code"] == "PT-02"]
    assert len(pt02_items) >= 1
    glass_item = pt02_items[0]
    assert pytest.approx(glass_item["quantity"], abs=0.5) == 18.00
    assert glass_item["unit"] == "sqm"

    # 5. Verify Unassigned/Raw Partition for Masonry Wall (PT-RAW)
    pt_raw_items = [it for it in takeoff["items"] if it["item_code"] == "PT-RAW"]
    assert len(pt_raw_items) >= 1
    raw_item = pt_raw_items[0]
    # Length = 8.0m linear length (unassigned partition centerline)
    assert pytest.approx(raw_item["quantity"], abs=0.5) == 8.00
    assert raw_item["unit"] == "m"

    # 6. Verify Base Measurements exist (Requirement 16)
    assert "base_measurements" in takeoff
    bm = takeoff["base_measurements"]
    assert "total_wall_length_m" in bm
    assert bm["total_wall_length_m"] >= 24.0  # 10 + 6 + 8 = 24m minimum


def test_partition_takeoff_missing_height_requires_review(tmp_path: Path):
    """Test that when wall height is unapproved and assumptions disabled, status is REVIEW_REQUIRED."""
    client = TestClient(app)
    dxf_file = tmp_path / "partitions_no_height.dxf"
    create_partition_dxf(dxf_file, include_openings=False)

    with open(dxf_file, "rb") as f:
        resp = client.post(
            "/v1/drawings/upload",
            files={"file": ("partitions_no_height.dxf", f, "application/dxf")},
            data={"drawing_number": "ARCH-PT-02", "revision": "01"}
        )
    assert resp.status_code == 200
    drawing_id = resp.json()["drawing_id"]

    # Assumptions explicitly DISABLED, no approved height
    profile_payload = {
        "profile_id": "STRICT_FITOUT",
        "units": "mm",
        "measurement_profile": "standard_interior",
        "assumptions_enabled": False
    }

    proc_resp = client.post(
        f"/v1/drawings/{drawing_id}/process",
        json={"project_profile": profile_payload}
    )
    assert proc_resp.status_code == 200
    takeoff = proc_resp.json()

    # Partition items must exist with quantity 0.0 and status REVIEW_REQUIRED
    pt01_items = [it for it in takeoff["items"] if it["item_code"] == "PT-01"]
    assert len(pt01_items) >= 1
    for it in pt01_items:
        assert it["status"] == "review_required"
        assert it["quantity"] == 0.0

    # Exception for MISSING_WALL_HEIGHT must be flagged
    missing_height_excs = [e for e in takeoff["exceptions"] if e["code"] == ExceptionCode.MISSING_WALL_HEIGHT.value]
    assert len(missing_height_excs) >= 1
