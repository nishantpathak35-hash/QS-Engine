"""
End-to-End Multi-Page Vector PDF API Test
Verifies Audit Finding #6:
- PDF Multi-Page must work through the actual API
- Page 1 has Room A, Page 2 has Room B
- Output contains merged quantities from both pages
- Every entity stores drawing_id, page_number, and page_scale
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from apps.api.main import app, DRAWINGS_DB, TAKEOFF_DB, GEOMETRY_DB

MM_TO_PT = 72.0 / 25.4


def create_two_page_pdf(file_path: Path) -> Path:
    """Creates a 2-page vector PDF: Page 1 = Room A (24 sqm), Page 2 = Room B (20 sqm)."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(file_path), pagesize=A4)
    width, height = A4

    # ---------------- PAGE 1 ----------------
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, "ARCHITECTURAL FLOOR PLAN - LEVEL 01")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 68, "Scale: 1:100 | Drawing No: ARCH-P01 | Rev: 01")

    # Room A: 6m x 4m -> 60mm x 40mm on paper -> 24 sqm
    conf_w_pt = 60.0 * MM_TO_PT
    conf_h_pt = 40.0 * MM_TO_PT
    origin_x = 100.0
    origin_y = height - 250.0

    c.setLineWidth(1.5)
    c.rect(origin_x, origin_y, conf_w_pt, conf_h_pt, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(origin_x + 30, origin_y + 55, "CONFERENCE ROOM")
    c.setFont("Helvetica", 8)
    c.drawString(origin_x + 40, origin_y + 40, "24.0 SQM")
    c.drawString(origin_x + 40, origin_y + 25, "F-01")

    c.showPage()  # Commit Page 1

    # ---------------- PAGE 2 ----------------
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, "ARCHITECTURAL FLOOR PLAN - LEVEL 02")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 68, "Scale: 1:100 | Drawing No: ARCH-P02 | Rev: 01")

    # Room B: 5m x 4m -> 50mm x 40mm on paper -> 20 sqm
    cabin_w_pt = 50.0 * MM_TO_PT
    cabin_h_pt = 40.0 * MM_TO_PT
    origin_x2 = 120.0
    origin_y2 = height - 260.0

    c.setLineWidth(1.5)
    c.rect(origin_x2, origin_y2, cabin_w_pt, cabin_h_pt, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(origin_x2 + 30, origin_y2 + 55, "EXECUTIVE CABIN")
    c.setFont("Helvetica", 8)
    c.drawString(origin_x2 + 40, origin_y2 + 40, "20.0 SQM")
    c.drawString(origin_x2 + 40, origin_y2 + 25, "F-01")

    c.showPage()  # Commit Page 2
    c.save()
    return file_path


def test_api_multipage_pdf_processes_all_pages(tmp_path: Path):
    """API must process all pages of a multi-page PDF, extract rooms from each, and merge takeoff."""
    client = TestClient(app)
    pdf_file = tmp_path / "multipage_architectural.pdf"
    create_two_page_pdf(pdf_file)

    # 1. Upload drawing through API
    with open(pdf_file, "rb") as f:
        upload_resp = client.post(
            "/v1/drawings/upload",
            files={"file": ("multipage_architectural.pdf", f, "application/pdf")},
            data={"drawing_number": "ARCH-MULTI-01", "revision": "01"}
        )
    assert upload_resp.status_code == 200
    drawing_id = upload_resp.json()["drawing_id"]

    # 2. Process drawing through API with explicit project profile enabling F-01
    profile_payload = {
        "profile_id": "TEST-MULTI-PDF",
        "units": "mm",
        "measurement_profile": "standard_interior",
        "assumptions_enabled": False,
        "room_finish_mapping_enabled": False
    }

    proc_resp = client.post(
        f"/v1/drawings/{drawing_id}/process",
        json={"project_profile": profile_payload}
    )
    assert proc_resp.status_code == 200
    takeoff_data = proc_resp.json()

    # 3. Assert quantities combine both Page 1 (24.0 sqm) and Page 2 (20.0 sqm) = 44.0 sqm
    fl01_items = [item for item in takeoff_data["items"] if item["item_code"] == "FL-01"]
    assert len(fl01_items) == 2, "Expected 2 FL-01 line items (one per page room)"
    total_fl01 = sum(item["quantity"] for item in fl01_items)
    assert pytest.approx(total_fl01, abs=0.5) == 44.0

    # Verify totals dictionary
    assert "FL-01" in takeoff_data["totals"]
    assert pytest.approx(takeoff_data["totals"]["FL-01"]["total_quantity"], abs=0.5) == 44.0

    # 4. Verify geometric persistence in GEOMETRY_DB with page attribution
    assert drawing_id in GEOMETRY_DB
    rooms = GEOMETRY_DB[drawing_id]["rooms"]
    assert len(rooms) == 2

    # Verify per-room page metadata
    conf_room = next((r for r in rooms if "CONFERENCE" in r.name), None)
    cabin_room = next((r for r in rooms if "EXECUTIVE" in r.name), None)

    assert conf_room is not None
    assert conf_room.page_number == 1
    assert conf_room.drawing_id == drawing_id
    assert conf_room.page_scale == 100
    assert pytest.approx(conf_room.net_area_sqm, abs=0.2) == 24.0

    assert cabin_room is not None
    assert cabin_room.page_number == 2
    assert cabin_room.drawing_id == drawing_id
    assert cabin_room.page_scale == 100
    assert pytest.approx(cabin_room.net_area_sqm, abs=0.2) == 20.0
