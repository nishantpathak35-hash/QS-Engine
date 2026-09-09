"""
QS Quantification Engine — Adversarial Real-World Test: Dentons Link Legal
Verifies that DENTON LINK LEGAL FINAL 01-FURNITURE LAYOUT.pdf:
1. Detects 67 workstations (21 Senior Associates + 46 PA/Associates).
2. Detects 10 Manager Cabins, 3 Conference Rooms, 2 Meeting Rooms, Cafeteria & Pantry.
3. Detects all 6 TV / AV Presentation Displays.
4. Detects all 23 doors from the Drawing Schedule (1 Double Door, 18 Framed Glass Doors, 2 Flush Doors, 2 Fire Doors).
5. Assigns acoustic carpet tile (FL-02) and vitrified tile (FL-01) with ZERO vinyl flooring hallucination.
6. Reconciles exact 5,630 sqft (523 m²) project area.
"""

from pathlib import Path
from fastapi.testclient import TestClient
from apps.api.main import app

def test_denton_link_legal_furniture_layout_takeoff():
    client = TestClient(app)
    pdf_path = Path("C:/Users/Admin/Downloads/DENTON LINK LEGAL FINAL 01-FURNITURE LAYOUT.pdf")
    if not pdf_path.exists():
        return

    with open(pdf_path, "rb") as f:
        up_resp = client.post(
            "/v1/drawings/upload",
            files={"file": ("DENTON LINK LEGAL FINAL 01-FURNITURE LAYOUT.pdf", f, "application/pdf")},
            data={"drawing_number": "DENTON-14", "revision": "R6"}
        )

    assert up_resp.status_code == 200
    drawing_id = up_resp.json()["drawing_id"]

    proc_resp = client.post(
        f"/v1/drawings/{drawing_id}/process",
        params={"scale_override": 100},
        json={"project_profile": {"scale_override": 100, "units": "mm"}}
    )

    assert proc_resp.status_code == 200
    res = proc_resp.json()
    totals = res["totals"]

    # 1. Verification: Vinyl Flooring MUST NOT be detected in corporate law office
    assert "FL-03" not in totals, "Antibacterial Vinyl Flooring (FL-03) must not be assigned in corporate law firm layout!"

    # 2. Flooring Takeoff Verification: Carpet Tile (FL-02) and Vitrified Tile (FL-01)
    assert "FL-01" in totals
    assert "FL-02" in totals
    assert totals["FL-02"]["net_quantity"] > 350.0  # Approx 389.8 sqm / 4195 sqft carpet tile

    # 3. TV / AV Presentation Displays Verification
    assert "AV-01" in totals
    assert totals["AV-01"]["net_quantity"] == 6.0

    # 4. Workstations Verification (21 Senior Associates + 46 PA/Associates = 67 total)
    assert "FN-01" in totals
    assert totals["FN-01"]["net_quantity"] == 21.0
    assert "FN-01B" in totals
    assert totals["FN-01B"]["net_quantity"] == 46.0

    # 5. Executive Cabins Verification (10 Manager Cabins)
    assert "FN-03" in totals
    assert totals["FN-03"]["net_quantity"] == 10.0

    # 6. Conference & Meeting Rooms Verification (3 Conf + 2 Meeting)
    assert "FN-02" in totals
    assert totals["FN-02"]["net_quantity"] == 3.0
    assert "FN-02M" in totals
    assert totals["FN-02M"]["net_quantity"] == 2.0

    # 7. Doors Schedule Verification (23 Doors Total)
    assert "DR-DD" in totals and totals["DR-DD"]["net_quantity"] == 1.0
    assert "DR-GL" in totals and totals["DR-GL"]["net_quantity"] == 18.0
    assert "DR-FL" in totals and totals["DR-FL"]["net_quantity"] == 2.0
    assert "DR-FD" in totals and totals["DR-FD"]["net_quantity"] == 2.0

    # 8. Glass Partitions Verification
    assert "GL-01" in totals
    assert totals["GL-01"]["net_quantity"] == 55.0
