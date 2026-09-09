"""
QS Quantification Engine — Adversarial Real-World Test
Guarantees AI Drawing Intelligence on real architectural layouts.
Verifies that BRIDGE WAY-FURNITURE LAYOUT.pdf extracts 38 workstations,
reconciles millwork storages, suppresses false drywall, and auto-calibrates scale.
"""

from pathlib import Path
from fastapi.testclient import TestClient
from apps.api.main import app

def test_bridgeway_furniture_layout_ai_takeoff():
    client = TestClient(app)
    pdf_path = Path("C:/Users/Admin/Downloads/BRIDGE WAY-FURNITURE LAYOUT.pdf")
    if not pdf_path.exists():
        return

    with open(pdf_path, "rb") as f:
        up_resp = client.post(
            "/v1/drawings/upload",
            files={"file": ("BRIDGE WAY-FURNITURE LAYOUT.pdf", f, "application/pdf")},
            data={"drawing_number": "BW-01", "revision": "01"}
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

    # 1. AI Intelligence Assertions
    ai = res["geometry"]["ai_insight"]
    assert ai["discipline"] == "FURNITURE_LAYOUT"
    assert ai["confidence"] >= 0.99
    assert len(ai["suppressed_trades"]) >= 2
    # Verify scale calibration (approx 13.2 mm/pt -> scale 37.5)
    assert 35.0 <= ai["scale_ratio"] <= 40.0

    # 2. Total & Takeoff Assertions
    totals = res["totals"]

    # Must NOT hallucinate 1022 m² gypsum drywall
    assert "PT-01" not in totals
    assert "PT-RAW" not in totals

    # Must extract exact 38 workstations
    assert "FN-01" in totals
    assert totals["FN-01"]["net_quantity"] == 38.0
    assert totals["FN-01"]["unit"] == "nos"

    # Must extract Conference Suite, Executive Suite, and Pantry
    assert "FN-02" in totals
    assert totals["FN-02"]["net_quantity"] == 1.0
    assert "FN-03" in totals
    assert totals["FN-03"]["net_quantity"] == 1.0
    assert "FN-04" in totals
    assert totals["FN-04"]["net_quantity"] == 1.0

    # Must extract Storages (MW-01, MW-02, MW-03)
    assert "MW-01" in totals
    assert totals["MW-01"]["net_quantity"] == 2.31
    assert "MW-02" in totals
    assert totals["MW-02"]["net_quantity"] == 11.15
    assert "MW-03" in totals
    assert totals["MW-03"]["net_quantity"] == 5.58

    # Must extract Toughened Glass Partition (GL-01) and Doors
    assert "GL-01" in totals
    assert totals["GL-01"]["net_quantity"] == 28.0
    assert "DR-GL" in totals
    assert totals["DR-GL"]["net_quantity"] == 2.0
    assert "DR-MD" in totals
    assert totals["DR-MD"]["net_quantity"] == 1.0

    # Must extract 55" LED TV
    assert "AV-01" in totals
    assert totals["AV-01"]["net_quantity"] == 1.0

    # 3. Architectural Spaces (5 verified spaces, NOT 54 fake 'O.H.S.' loops)
    rooms = res["geometry"]["rooms"]
    assert len(rooms) == 5
    room_names = [r["name"] for r in rooms]
    assert any("Workstation Hall" in name for name in room_names)
    assert any("Conference Room" in name for name in room_names)
    assert any("Director" in name for name in room_names)
    assert any("Dry Pantry" in name for name in room_names)
    assert not any("O.H.S." in name for name in room_names)
