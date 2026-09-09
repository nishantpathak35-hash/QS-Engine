"""
Unit Tests for Elimination of Silent Assumptions
Directly addresses Audit P0 Finding #5:
Never silently assume DXF units = mm or door orientation = horizontal.
"""

from pathlib import Path
import pytest
import ezdxf
from core.geometry.primitives import Point2D, Segment2D
from core.exceptions import UnitRequiredError
from core.models.semantics import Opening, OpeningType
from parsers.dxf.reader import DXFParser
from semantics.rooms.boundary_solver import RoomBoundarySolver

def test_unitless_dxf_raises_unit_required(tmp_path: Path):
    """A DXF with $INSUNITS = 0 must raise UnitRequiredError if no user assumption is provided."""
    dxf_path = tmp_path / "unitless.dxf"
    doc = ezdxf.new("R2010")
    # Set units to 0 (unspecified / unitless)
    doc.header["$INSUNITS"] = 0
    msp = doc.modelspace()
    msp.add_line((0, 0), (100, 100))
    doc.saveas(str(dxf_path))

    parser = DXFParser()
    with pytest.raises(UnitRequiredError) as exc_info:
        parser.parse_file(dxf_path, assumed_units=None)

    assert "unspecified units ($INSUNITS=0)" in str(exc_info.value)


def test_unitless_dxf_accepts_explicit_user_assumption(tmp_path: Path):
    """When the user explicitly provides assumed_units='mm', the drawing parses and logs an assumption."""
    dxf_path = tmp_path / "unitless_with_assumption.dxf"
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 0
    msp = doc.modelspace()
    msp.add_line((0, 0), (1000, 1000))
    doc.saveas(str(dxf_path))

    parser = DXFParser()
    parsed = parser.parse_file(dxf_path, assumed_units="mm")
    assert parsed.scale_to_mm == 1.0
    assert len(parsed.assumptions) == 1
    assert "applied user-approved default: mm" in parsed.assumptions[0]


def test_vertical_door_orientation_closes_vertical_wall():
    """A door on a vertical wall (90 deg orientation) must create a vertical threshold line and close the boundary."""
    solver = RoomBoundarySolver()

    # Room: 6m wide x 8m tall.
    # Vertical East wall has a 1000mm door opening from (6000, 3000) to (6000, 4000).
    walls = [
        # South wall
        Segment2D(start=Point2D(0, 0), end=Point2D(6000, 0)),
        # East wall (bottom piece)
        Segment2D(start=Point2D(6000, 0), end=Point2D(6000, 3000)),
        # [Door opening from (6000, 3000) to (6000, 4000)]
        # East wall (top piece)
        Segment2D(start=Point2D(6000, 4000), end=Point2D(6000, 8000)),
        # North wall
        Segment2D(start=Point2D(6000, 8000), end=Point2D(0, 8000)),
        # West wall
        Segment2D(start=Point2D(0, 8000), end=Point2D(0, 0)),
    ]

    # Vertical door opening with orientation_deg = 90
    vertical_door = Opening(
        id="D-VERT",
        opening_type=OpeningType.DOOR,
        width_m=1.0,
        location=Point2D(6000, 3000),
        orientation_deg=90.0,
        jamb_p1=Point2D(6000, 3000),
        jamb_p2=Point2D(6000, 4000)
    )

    # Without the door, room is open and cannot be polygonized
    rooms_without_door = solver.solve_rooms(walls, [])
    assert len(rooms_without_door) == 0, "Room must not close when there is an unbridged 1000mm gap!"

    # With the vertical door threshold, boundary is closed
    rooms_with_door = solver.solve_rooms(walls, [], door_openings=[vertical_door])
    assert len(rooms_with_door) == 1, "Vertical door threshold must successfully bridge the vertical wall gap!"
    assert pytest.approx(rooms_with_door[0].net_area_sqm, abs=0.01) == 48.00  # 6m x 8m = 48 sqm
