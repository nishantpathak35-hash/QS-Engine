"""
QS Quantification Engine — AutoCAD DXF Geometry & Entity Parser
Deterministic extraction of lines, polylines, arcs, texts, blocks, and layers.
Enforces Blueprint Section 10, Section 11, Section 70, and Section 71.
"""

from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass, field
import ezdxf
from ezdxf.document import Drawing

from core.geometry.primitives import Point2D, Segment2D, Arc2D
from core.exceptions import UnitRequiredError, UnsupportedUnitError
from parsers.dxf.layer_classifier import LayerMappingProfile, LayerCategory, LayerClassifier

INSUNITS_TO_MM = {
    1: 25.4,        # Inches
    2: 304.8,       # Feet
    4: 1.0,         # Millimeters
    5: 10.0,        # Centimeters
    6: 1000.0,      # Meters
}

UNIT_NAME_TO_MM = {
    "mm": 1.0,
    "millimeter": 1.0,
    "millimeters": 1.0,
    "cm": 10.0,
    "centimeter": 10.0,
    "m": 1000.0,
    "meter": 1000.0,
    "meters": 1000.0,
    "inch": 25.4,
    "inches": 25.4,
    "feet": 304.8,
    "foot": 304.8
}


@dataclass
class ExtractedText:
    content: str
    location: Point2D
    height_mm: float
    rotation_deg: float = 0.0
    layer: str = "0"
    handle: str = ""


@dataclass
class ExtractedBlock:
    name: str
    location: Point2D
    rotation_deg: float = 0.0
    layer: str = "0"
    handle: str = ""
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass
class ParsedDXFDrawing:
    filename: str
    dxf_version: str
    drawing_units: str
    scale_to_mm: float
    segments: list[Segment2D] = field(default_factory=list)
    arcs: list[Arc2D] = field(default_factory=list)
    texts: list[ExtractedText] = field(default_factory=list)
    blocks: list[ExtractedBlock] = field(default_factory=list)
    layers: set[str] = field(default_factory=set)
    assumptions: list[str] = field(default_factory=list)

    def get_segments_by_category(self, category: LayerCategory, classifier: LayerClassifier) -> list[Segment2D]:
        return [
            seg for seg in self.segments
            if classifier.classify_layer(seg.layer) == category
        ]


class DXFParser:
    """Deterministic parser extracting geometric and semantic entities from DXF."""

    def __init__(self, layer_profile: LayerMappingProfile | None = None):
        self.layer_profile = layer_profile or LayerMappingProfile()

    def parse_file(
        self,
        file_path: str | Path,
        assumed_units: str | None = None
    ) -> ParsedDXFDrawing:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"DXF file not found: {path}")

        doc: Drawing = ezdxf.readfile(str(path))
        return self._extract_drawing(doc, path.name, assumed_units=assumed_units)

    def _extract_drawing(
        self,
        doc: Drawing,
        filename: str,
        assumed_units: str | None = None
    ) -> ParsedDXFDrawing:
        assumptions: list[str] = []
        insunits = doc.header.get("$INSUNITS", 0)

        if insunits in INSUNITS_TO_MM:
            scale_to_mm = INSUNITS_TO_MM[insunits]
            unit_name = {1: "inches", 2: "feet", 4: "mm", 5: "cm", 6: "m"}[insunits]
        elif insunits == 0:
            # Unspecified / Unitless drawing
            if assumed_units:
                unit_lower = assumed_units.lower()
                if unit_lower not in UNIT_NAME_TO_MM:
                    raise ValueError(f"Unrecognized assumed unit: {assumed_units}")
                scale_to_mm = UNIT_NAME_TO_MM[unit_lower]
                unit_name = f"{assumed_units} (user-approved assumption)"
                assumptions.append(f"Drawing units were unspecified ($INSUNITS=0); applied user-approved default: {assumed_units}")
            else:
                raise UnitRequiredError(
                    f"Drawing '{filename}' has unspecified units ($INSUNITS=0). "
                    f"Set assumed_units (e.g. 'mm', 'm') or calibrate scale."
                )
        else:
            raise UnsupportedUnitError(
                f"Drawing '{filename}' has unsupported unit code $INSUNITS={insunits}. "
                f"Supported units: 1 (inches), 2 (feet), 4 (mm), 5 (cm), 6 (meters)."
            )

        msp = doc.modelspace()
        segments: list[Segment2D] = []
        arcs: list[Arc2D] = []
        texts: list[ExtractedText] = []
        blocks: list[ExtractedBlock] = []
        layers: set[str] = set()

        for entity in msp:
            layer = entity.dxf.layer
            layers.add(layer)
            handle = entity.dxf.handle
            dxftype = entity.dxftype()

            if dxftype == "LINE":
                p1 = Point2D(entity.dxf.start.x * scale_to_mm, entity.dxf.start.y * scale_to_mm)
                p2 = Point2D(entity.dxf.end.x * scale_to_mm, entity.dxf.end.y * scale_to_mm)
                segments.append(Segment2D(start=p1, end=p2, layer=layer, handle=handle))

            elif dxftype == "LWPOLYLINE":
                points = [Point2D(p[0] * scale_to_mm, p[1] * scale_to_mm) for p in entity.get_points()]
                is_closed = entity.is_closed
                for i in range(len(points) - 1):
                    segments.append(Segment2D(start=points[i], end=points[i+1], layer=layer, handle=handle))
                if is_closed and len(points) > 2:
                    segments.append(Segment2D(start=points[-1], end=points[0], layer=layer, handle=handle))

            elif dxftype == "POLYLINE":
                try:
                    points = [Point2D(v.dxf.location.x * scale_to_mm, v.dxf.location.y * scale_to_mm) for v in entity.vertices]
                    is_closed = entity.is_closed
                    for i in range(len(points) - 1):
                        segments.append(Segment2D(start=points[i], end=points[i+1], layer=layer, handle=handle))
                    if is_closed and len(points) > 2:
                        segments.append(Segment2D(start=points[-1], end=points[0], layer=layer, handle=handle))
                except Exception:
                    pass

            elif dxftype == "ARC":
                center = Point2D(entity.dxf.center.x * scale_to_mm, entity.dxf.center.y * scale_to_mm)
                arcs.append(Arc2D(
                    center=center,
                    radius=entity.dxf.radius * scale_to_mm,
                    start_angle_deg=entity.dxf.start_angle,
                    end_angle_deg=entity.dxf.end_angle,
                    layer=layer,
                    handle=handle
                ))

            elif dxftype == "CIRCLE":
                center = Point2D(entity.dxf.center.x * scale_to_mm, entity.dxf.center.y * scale_to_mm)
                arcs.append(Arc2D(
                    center=center,
                    radius=entity.dxf.radius * scale_to_mm,
                    start_angle_deg=0.0,
                    end_angle_deg=360.0,
                    layer=layer,
                    handle=handle
                ))

            elif dxftype in ("TEXT", "MTEXT"):
                text_content = entity.dxf.text if dxftype == "TEXT" else entity.text
                insert = entity.dxf.insert
                location = Point2D(insert.x * scale_to_mm, insert.y * scale_to_mm)
                height = (entity.dxf.height if hasattr(entity.dxf, "height") else 2.5) * scale_to_mm
                rotation = entity.dxf.rotation if hasattr(entity.dxf, "rotation") else 0.0
                texts.append(ExtractedText(
                    content=text_content.strip(),
                    location=location,
                    height_mm=height,
                    rotation_deg=rotation,
                    layer=layer,
                    handle=handle
                ))

            elif dxftype == "INSERT":
                insert = entity.dxf.insert
                location = Point2D(insert.x * scale_to_mm, insert.y * scale_to_mm)
                rotation = entity.dxf.rotation if hasattr(entity.dxf, "rotation") else 0.0
                attribs = {}
                if hasattr(entity, "attribs"):
                    for a in entity.attribs:
                        attribs[a.dxf.tag] = a.dxf.text
                blocks.append(ExtractedBlock(
                    name=entity.dxf.name,
                    location=location,
                    rotation_deg=rotation,
                    layer=layer,
                    handle=handle,
                    attributes=attribs
                ))

        return ParsedDXFDrawing(
            filename=filename,
            dxf_version=doc.dxfversion,
            drawing_units=unit_name,
            scale_to_mm=scale_to_mm,
            segments=segments,
            arcs=arcs,
            texts=texts,
            blocks=blocks,
            layers=layers,
            assumptions=assumptions
        )
