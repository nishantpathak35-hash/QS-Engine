"""
Synthetic DXF Generator for Benchmark & Golden Regression Testing
Generates mathematically verified AutoCAD DXF drawings with known dimensions.
Enforces Blueprint Section 49 (Golden Drawing Test System).
"""

from pathlib import Path
import ezdxf
from ezdxf.document import Drawing

def create_synthetic_office_dxf(output_path: str | Path) -> Path:
    """
    Creates an AutoCAD DXF with 2 adjacent rooms:
    1. Conference Room: 6000mm x 4000mm = 24.000 sqm, Perimeter = 20.000 m
       Door opening: 900mm width at (3000, 0)
    2. Executive Cabin: 4000mm x 4000mm = 16.000 sqm, Perimeter = 16.000 m
       Door opening: 900mm width at (7000, 0)
    Shared interior partition wall at x = 6000 from y = 0 to y = 4000.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    doc: Drawing = ezdxf.new("R2010")
    # Set modelspace units to Millimeters (4)
    doc.header["$INSUNITS"] = 4

    # Create CAD Layers
    doc.layers.add("A-WALL", color=7)
    doc.layers.add("A-DOOR", color=1)
    doc.layers.add("A-ANNO", color=3)
    doc.layers.add("F-FURN", color=4)

    msp = doc.modelspace()

    # Outer and interior wall segments (centerline)
    # Conference Room: (0,0) to (6000, 4000)
    # Executive Cabin: (6000,0) to (10000, 4000)
    wall_lines = [
        # South walls
        ((0, 0), (3000, 0)),
        ((3900, 0), (6000, 0)),
        ((6000, 0), (7000, 0)),
        ((7900, 0), (10000, 0)),
        # East wall
        ((10000, 0), (10000, 4000)),
        # North wall
        ((10000, 4000), (0, 4000)),
        # West wall
        ((0, 4000), (0, 0)),
        # Partition wall separating Conference Room & Cabin
        ((6000, 0), (6000, 4000))
    ]

    for start, end in wall_lines:
        msp.add_line(start, end, dxfattribs={"layer": "A-WALL"})

    # Room Labels and Explicit Finish Codes (Evidence-Driven)
    msp.add_text("CONFERENCE ROOM", dxfattribs={
        "layer": "A-ANNO",
        "height": 250,
        "insert": (2500, 2000)
    })
    msp.add_text("F-01", dxfattribs={
        "layer": "A-ANNO",
        "height": 180,
        "insert": (2500, 1500)
    })
    msp.add_text("SK-01", dxfattribs={
        "layer": "A-ANNO",
        "height": 180,
        "insert": (2500, 1200)
    })

    msp.add_text("EXECUTIVE CABIN", dxfattribs={
        "layer": "A-ANNO",
        "height": 250,
        "insert": (7500, 2000)
    })
    msp.add_text("F-01", dxfattribs={
        "layer": "A-ANNO",
        "height": 180,
        "insert": (7500, 1500)
    })
    msp.add_text("SK-01", dxfattribs={
        "layer": "A-ANNO",
        "height": 180,
        "insert": (7500, 1200)
    })

    # Door Block definition & insertions
    door_block = doc.blocks.new("DOOR_SINGLE_900")
    door_block.add_line((0, 0), (900, 0))
    door_block.add_arc(center=(0, 0), radius=900, start_angle=0, end_angle=90)

    # Insert Door D1 for Conference Room
    msp.add_blockref("DOOR_SINGLE_900", insert=(3000, 0), dxfattribs={"layer": "A-DOOR"})
    # Insert Door D2 for Cabin
    msp.add_blockref("DOOR_SINGLE_900", insert=(7000, 0), dxfattribs={"layer": "A-DOOR"})

    doc.saveas(str(path))
    return path
