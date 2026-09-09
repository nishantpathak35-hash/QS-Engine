"""
Adversarial Tests — DXF Entity Extraction
Validates parsing of CIRCLE and 2D POLYLINE entities.
Enforces Audit Requirement 9.
"""

import pytest
from pathlib import Path
import ezdxf

from parsers.dxf.reader import DXFParser


def test_dxf_circle_and_polyline_parsing(tmp_path: Path):
    """DXF parser must extract CIRCLE entities as 360-deg arcs and POLYLINE as segments."""
    dxf_path = tmp_path / "test_primitives.dxf"
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 4  # mm
    msp = doc.modelspace()

    # Add a CIRCLE (e.g. column or symbol)
    msp.add_circle(center=(2000, 3000), radius=250, dxfattribs={"layer": "S-COL"})

    # Add a 2D POLYLINE
    msp.add_polyline2d([(0, 0), (1000, 0), (1000, 1000), (0, 1000)], close=True, dxfattribs={"layer": "A-WALL"})

    doc.saveas(str(dxf_path))

    parser = DXFParser()
    parsed = parser.parse_file(dxf_path)

    # Verify Circle
    circles = [a for a in parsed.arcs if a.start_angle_deg == 0.0 and a.end_angle_deg == 360.0]
    assert len(circles) == 1
    assert circles[0].radius_mm == 250.0
    assert circles[0].center.x == 2000.0
    assert circles[0].center.y == 3000.0

    # Verify Polyline segments
    wall_segs = [s for s in parsed.segments if s.layer == "A-WALL"]
    assert len(wall_segs) == 4
