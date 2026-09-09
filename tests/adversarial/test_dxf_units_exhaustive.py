"""
Exhaustive Tests for DXF Unit Codes & Validation
Tests Blueprint Section 10 & Audit Finding #9:
- Supported explicit units: inches (1), feet (2), mm (4), cm (5), m (6)
- Unitless (0): raises UnitRequiredError without assumed_units, succeeds with assumed_units
- Unsupported unit codes: raises UnsupportedUnitError, prevents silent takeoff fallback
- API integration: blocks takeoff, returns UNSUPPORTED_UNIT / UNIT_REQUIRED exception
"""

from pathlib import Path
import pytest
import ezdxf
from fastapi.testclient import TestClient

from parsers.dxf.reader import DXFParser, INSUNITS_TO_MM
from core.exceptions import UnitRequiredError, UnsupportedUnitError
from core.exception_registry import ExceptionCode
from apps.api.main import app, DRAWINGS_DB, TAKEOFF_DB, EXCEPTION_REGISTRY


@pytest.mark.parametrize("insunits,expected_scale,expected_name", [
    (1, 25.4, "inches"),
    (2, 304.8, "feet"),
    (4, 1.0, "mm"),
    (5, 10.0, "cm"),
    (6, 1000.0, "m"),
])
def test_all_supported_dxf_units(tmp_path: Path, insunits: int, expected_scale: float, expected_name: str):
    """Every supported $INSUNITS code must map to exact mm scale factor."""
    dxf_file = tmp_path / f"test_unit_{insunits}.dxf"
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = insunits
    msp = doc.modelspace()
    msp.add_line((0, 0), (10, 10))
    doc.saveas(str(dxf_file))

    parser = DXFParser()
    parsed = parser.parse_file(dxf_file)
    assert parsed.scale_to_mm == pytest.approx(expected_scale)
    assert parsed.drawing_units == expected_name


@pytest.mark.parametrize("unsupported_code", [3, 7, 8, 9, 10, 14, 99])
def test_unsupported_dxf_units_raise_error(tmp_path: Path, unsupported_code: int):
    """Any unsupported $INSUNITS code must raise UnsupportedUnitError and NEVER silently default to 1.0."""
    dxf_file = tmp_path / f"test_unsupported_{unsupported_code}.dxf"
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = unsupported_code
    msp = doc.modelspace()
    msp.add_line((0, 0), (10, 10))
    doc.saveas(str(dxf_file))

    parser = DXFParser()
    with pytest.raises(UnsupportedUnitError) as exc_info:
        parser.parse_file(dxf_file)

    assert f"$INSUNITS={unsupported_code}" in str(exc_info.value)
    assert "unsupported unit code" in str(exc_info.value).lower()


def test_unitless_dxf_requires_units(tmp_path: Path):
    """$INSUNITS=0 without assumed_units must raise UnitRequiredError."""
    dxf_file = tmp_path / "unitless.dxf"
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 0
    msp = doc.modelspace()
    msp.add_line((0, 0), (10, 10))
    doc.saveas(str(dxf_file))

    parser = DXFParser()
    with pytest.raises(UnitRequiredError) as exc_info:
        parser.parse_file(dxf_file)

    assert "unspecified units ($INSUNITS=0)" in str(exc_info.value)


@pytest.mark.parametrize("assumed,expected_scale", [
    ("mm", 1.0),
    ("cm", 10.0),
    ("m", 1000.0),
    ("inches", 25.4),
    ("feet", 304.8),
])
def test_unitless_dxf_with_valid_assumed_units(tmp_path: Path, assumed: str, expected_scale: float):
    """$INSUNITS=0 with user-approved assumed_units converts accurately."""
    dxf_file = tmp_path / f"unitless_assumed_{assumed}.dxf"
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 0
    msp = doc.modelspace()
    msp.add_line((0, 0), (10, 10))
    doc.saveas(str(dxf_file))

    parser = DXFParser()
    parsed = parser.parse_file(dxf_file, assumed_units=assumed)
    assert parsed.scale_to_mm == pytest.approx(expected_scale)
    assert assumed in parsed.drawing_units


def test_api_stops_takeoff_on_unsupported_unit(tmp_path: Path):
    """API must stop takeoff and return UNSUPPORTED_UNIT exception when DXF has unsupported units."""
    client = TestClient(app)
    dxf_file = tmp_path / "api_unsupported.dxf"
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 99  # Unsupported
    msp = doc.modelspace()
    msp.add_line((0, 0), (1000, 0), dxfattribs={"layer": "WALLS"})
    msp.add_line((1000, 0), (1000, 1000), dxfattribs={"layer": "WALLS"})
    msp.add_line((1000, 1000), (0, 1000), dxfattribs={"layer": "WALLS"})
    msp.add_line((0, 1000), (0, 0), dxfattribs={"layer": "WALLS"})
    doc.saveas(str(dxf_file))

    with open(dxf_file, "rb") as f:
        upload_resp = client.post(
            "/v1/drawings/upload",
            files={"file": ("api_unsupported.dxf", f, "application/dxf")},
            data={"drawing_number": "DWG-UNSUP-01", "revision": "A"}
        )
    assert upload_resp.status_code == 200
    drawing_id = upload_resp.json()["drawing_id"]

    # Process drawing
    proc_resp = client.post(f"/v1/drawings/{drawing_id}/process")
    assert proc_resp.status_code == 200
    data = proc_resp.json()
    assert len(data["items"]) == 0
    assert any(e["code"] == "UNSUPPORTED_UNIT" for e in data["exceptions"])


def test_api_stops_takeoff_on_unitless_without_assumed(tmp_path: Path):
    """API must stop takeoff and return UNIT_REQUIRED exception when DXF is unitless and no assumed_units provided."""
    client = TestClient(app)
    dxf_file = tmp_path / "api_unitless.dxf"
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 0
    msp = doc.modelspace()
    msp.add_line((0, 0), (1000, 0), dxfattribs={"layer": "WALLS"})
    msp.add_line((1000, 0), (1000, 1000), dxfattribs={"layer": "WALLS"})
    msp.add_line((1000, 1000), (0, 1000), dxfattribs={"layer": "WALLS"})
    msp.add_line((0, 1000), (0, 0), dxfattribs={"layer": "WALLS"})
    doc.saveas(str(dxf_file))

    with open(dxf_file, "rb") as f:
        upload_resp = client.post(
            "/v1/drawings/upload",
            files={"file": ("api_unitless.dxf", f, "application/dxf")},
            data={"drawing_number": "DWG-UNITLESS-01", "revision": "A"}
        )
    assert upload_resp.status_code == 200
    drawing_id = upload_resp.json()["drawing_id"]

    # Process drawing without assumed_units
    proc_resp = client.post(f"/v1/drawings/{drawing_id}/process")
    assert proc_resp.status_code == 200
    data = proc_resp.json()
    assert len(data["items"]) == 0
    assert any(e["code"] == "UNIT_REQUIRED" for e in data["exceptions"])
