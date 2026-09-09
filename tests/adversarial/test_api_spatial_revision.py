"""
End-to-End API Spatial Revision Test
Verifies Audit Finding #8 & #19:
- Revision comparison through API must pass persisted geometry
- Renamed room (Conference Room -> Boardroom) with identical geometry
- Must return MODIFIED, not REMOVED + ADDED
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import ezdxf

from apps.api.main import app, DRAWINGS_DB, TAKEOFF_DB, GEOMETRY_DB


def create_dxf_drawing(file_path: Path, room_name: str, x: float = 0, y: float = 0, w: float = 6000, h: float = 4000):
    """Creates a DXF with 4 wall lines and a room label text."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 4  # mm
    msp = doc.modelspace()

    # Add 4 walls on WALLS layer
    msp.add_line((x, y), (x + w, y), dxfattribs={"layer": "WALLS"})
    msp.add_line((x + w, y), (x + w, y + h), dxfattribs={"layer": "WALLS"})
    msp.add_line((x + w, y + h), (x, y + h), dxfattribs={"layer": "WALLS"})
    msp.add_line((x, y + h), (x, y), dxfattribs={"layer": "WALLS"})

    # Add room name and finish text
    msp.add_text(room_name, dxfattribs={"layer": "ROOM_NAMES", "height": 250}).set_placement((x + 1000, y + 2000))
    msp.add_text("F-01", dxfattribs={"layer": "FINISHES", "height": 200}).set_placement((x + 1000, y + 1500))

    doc.saveas(str(file_path))
    return file_path


def test_api_revision_detects_spatial_rename_as_modified(tmp_path: Path):
    """API revision compare must detect renamed room with identical geometry as MODIFIED, not ADDED/REMOVED."""
    client = TestClient(app)

    # 1. Create and upload Revision A: "CONFERENCE ROOM"
    rev_a_file = tmp_path / "plan_rev_a.dxf"
    create_dxf_drawing(rev_a_file, room_name="CONFERENCE ROOM")

    with open(rev_a_file, "rb") as f:
        resp_a = client.post(
            "/v1/drawings/upload",
            files={"file": ("plan_rev_a.dxf", f, "application/dxf")},
            data={"drawing_number": "A-100", "revision": "A"}
        )
    assert resp_a.status_code == 200
    id_a = resp_a.json()["drawing_id"]

    # 2. Create and upload Revision B: "BOARDROOM" with identical spatial geometry
    rev_b_file = tmp_path / "plan_rev_b.dxf"
    create_dxf_drawing(rev_b_file, room_name="BOARDROOM")

    with open(rev_b_file, "rb") as f:
        resp_b = client.post(
            "/v1/drawings/upload",
            files={"file": ("plan_rev_b.dxf", f, "application/dxf")},
            data={"drawing_number": "A-100", "revision": "B"}
        )
    assert resp_b.status_code == 200
    id_b = resp_b.json()["drawing_id"]

    # 3. Process both drawings through API
    profile_payload = {
        "profile_id": "REVISION-TEST-PROFILE",
        "units": "mm",
        "measurement_profile": "standard_interior",
        "assumptions_enabled": False,
        "room_finish_mapping_enabled": False
    }

    proc_a = client.post(f"/v1/drawings/{id_a}/process", json={"project_profile": profile_payload})
    assert proc_a.status_code == 200

    proc_b = client.post(f"/v1/drawings/{id_b}/process", json={"project_profile": profile_payload})
    assert proc_b.status_code == 200

    # 4. Verify geometry is persisted in GEOMETRY_DB for both drawings
    assert id_a in GEOMETRY_DB and len(GEOMETRY_DB[id_a]["rooms"]) == 1
    assert id_b in GEOMETRY_DB and len(GEOMETRY_DB[id_b]["rooms"]) == 1

    # 5. Call API /v1/revisions/compare
    compare_resp = client.post(f"/v1/revisions/compare?baseline_id={id_a}&revised_id={id_b}")
    assert compare_resp.status_code == 200
    comp_data = compare_resp.json()

    # 6. Check summary counts
    summary = comp_data["summary"]
    assert summary["added_count"] == 0, f"Expected 0 added items, got {summary['added_count']}"
    assert summary["removed_count"] == 0, f"Expected 0 removed items, got {summary['removed_count']}"
    assert summary["modified_count"] > 0, f"Expected modified items from rename, got {summary['modified_count']}"

    # 7. Check line item details
    deltas = comp_data["deltas"]
    fl_delta = next((d for d in deltas if d["item_code"] == "FL-01"), None)
    assert fl_delta is not None
    assert fl_delta["change_type"] == "modified"
    assert "Renamed from 'CONFERENCE ROOM'" in fl_delta["description"]
    assert fl_delta["spatial_similarity"] >= 0.95
