"""
Integration Tests for FastAPI Application Gateway
Tests upload, processing, quantities retrieval, and Excel/CSV exports.
Enforces Blueprint Section 45 (API Design).
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from apps.api.main import app
from tests.fixtures.synthetic_dxf import create_synthetic_office_dxf

client = TestClient(app)

def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["deterministic_core"] is True

def test_end_to_end_dxf_upload_process_and_export(tmp_path: Path):
    # 1. Create a synthetic test DXF
    dxf_path = tmp_path / "api_test_drawing.dxf"
    create_synthetic_office_dxf(dxf_path)

    # 2. Upload DXF via POST /v1/drawings/upload
    with open(dxf_path, "rb") as f:
        res_upload = client.post(
            "/v1/drawings/upload",
            files={"file": ("api_test_drawing.dxf", f, "application/dxf")},
            data={"drawing_number": "A-101", "revision": "03"}
        )

    assert res_upload.status_code == 200
    upload_data = res_upload.json()
    drawing_id = upload_data["drawing_id"]
    assert upload_data["file_type"] == "dxf"

    # 3. Process Drawing via POST /v1/drawings/{id}/process
    res_process = client.post(f"/v1/drawings/{drawing_id}/process")
    assert res_process.status_code == 200
    takeoff_data = res_process.json()

    assert takeoff_data["drawing_id"] == drawing_id
    assert len(takeoff_data["items"]) >= 4
    # Flooring total = 40.0 sqm
    assert takeoff_data["totals"]["FL-01"]["total_quantity"] == 40.0
    assert takeoff_data["totals"]["DR-01"]["total_quantity"] == 2.0

    # 4. Query Quantities via GET /v1/drawings/{id}/quantities
    res_qty = client.get(f"/v1/drawings/{drawing_id}/quantities")
    assert res_qty.status_code == 200
    assert res_qty.json()["totals"]["FL-01"]["total_quantity"] == 40.0

    # 5. Export Excel via GET /v1/drawings/{id}/export?format=excel
    res_excel = client.get(f"/v1/drawings/{drawing_id}/export?format=excel")
    assert res_excel.status_code == 200
    assert "spreadsheetml" in res_excel.headers["content-type"]
    assert len(res_excel.content) > 1000

    # 6. Export CSV via GET /v1/drawings/{id}/export?format=csv
    res_csv = client.get(f"/v1/drawings/{drawing_id}/export?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert b"FL-01" in res_csv.content
