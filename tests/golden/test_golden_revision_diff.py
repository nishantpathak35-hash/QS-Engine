"""
Golden Drawing Revision Comparison Integration Test
Tests end-to-end multi-revision upload, processing, and delta generation via REST API.
Enforces Blueprint Section 38 & Section 39.
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from apps.api.main import app
from tests.fixtures.synthetic_dxf import create_synthetic_office_dxf

client = TestClient(app)

def test_golden_api_revision_comparison(tmp_path: Path):
    # 1. Create Rev 01 DXF
    dxf_rev1 = tmp_path / "office_rev01.dxf"
    create_synthetic_office_dxf(dxf_rev1)

    # 2. Upload and Process Rev 01
    with open(dxf_rev1, "rb") as f:
        res1 = client.post(
            "/v1/drawings/upload",
            files={"file": ("office_rev01.dxf", f, "application/dxf")},
            data={"drawing_number": "A-101", "revision": "01"}
        )
    id1 = res1.json()["drawing_id"]
    client.post(f"/v1/drawings/{id1}/process")

    # 3. Create & Upload Rev 02
    dxf_rev2 = tmp_path / "office_rev02.dxf"
    create_synthetic_office_dxf(dxf_rev2)
    with open(dxf_rev2, "rb") as f:
        res2 = client.post(
            "/v1/drawings/upload",
            files={"file": ("office_rev02.dxf", f, "application/dxf")},
            data={"drawing_number": "A-101", "revision": "02"}
        )
    id2 = res2.json()["drawing_id"]
    client.post(f"/v1/drawings/{id2}/process")

    # 4. Compare Revisions via POST /v1/revisions/compare
    res_compare = client.post(f"/v1/revisions/compare?baseline_id={id1}&revised_id={id2}")
    assert res_compare.status_code == 200
    data = res_compare.json()

    assert data["baseline_revision"] == "01"
    assert data["revised_revision"] == "02"
    assert "summary" in data
    assert data["summary"]["total_items_compared"] > 0
    # Because identical drawings were uploaded, all items should be UNCHANGED
    assert data["summary"]["unchanged_count"] == data["summary"]["total_items_compared"]
    assert data["summary"]["modified_count"] == 0
