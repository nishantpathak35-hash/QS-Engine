"""
QS Quantification Engine — Viewer Data Serializer
Converts parsed DXF geometry, solved room polygons, and takeoff items to JSON for the Web Viewer.
"""

from pathlib import Path
import json
from tests.fixtures.synthetic_dxf import create_synthetic_office_dxf
from parsers.dxf.reader import DXFParser
from parsers.dxf.layer_classifier import LayerCategory
from semantics.rooms.boundary_solver import RoomBoundarySolver
from qs.rule_engine import QSRuleEngine
from core.models.semantics import Opening, OpeningType

from parsers.classifier import DrawingTypeClassifier, DrawingType
from parsers.pdf_vector.extractor import VectorPDFExtractor

def generate_viewer_data(file_path: str | Path, output_json: str | Path) -> dict:
    path = Path(file_path)
    classification = DrawingTypeClassifier.classify_file(path)

    if classification.overall_type == DrawingType.VECTOR_PDF:
        extractor = VectorPDFExtractor()
        parsed_pdf = extractor.extract_page(path, page_number=1)
        solver = RoomBoundarySolver()
        rooms = solver.solve_rooms(parsed_pdf.segments, parsed_pdf.texts)
        rule_engine = QSRuleEngine()
        takeoff = rule_engine.calculate_takeoff(
            drawing_id="DRW-PDF-001",
            drawing_number="A-101",
            revision="02",
            rooms=rooms
        )
        data = {
            "drawing": {
                "filename": path.name,
                "drawing_number": "A-101",
                "revision": "02",
                "units": "mm",
                "scale_to_mm": parsed_pdf.scale.scale_factor_mm_per_pt
            },
            "layers": ["PDF_VECTOR", "ROOM_OVERLAYS"],
            "segments": [
                {
                    "x1": round(s.start.x, 2),
                    "y1": round(s.start.y, 2),
                    "x2": round(s.end.x, 2),
                    "y2": round(s.end.y, 2),
                    "layer": s.layer,
                    "handle": s.handle
                }
                for s in parsed_pdf.segments[:100]  # sample segments for fast render
            ],
            "rooms": [
                {
                    "id": r.id,
                    "name": r.name,
                    "net_area_sqm": round(r.net_area_sqm, 2),
                    "gross_area_sqm": round(r.gross_area_sqm, 2),
                    "perimeter_m": round(r.perimeter_m, 2),
                    "confidence": r.confidence,
                    "status": r.status.value,
                    "polygon": [[round(p.x, 2), round(p.y, 2)] for p in r.polygon.vertices]
                }
                for r in rooms
            ],
            "takeoff": [item.to_dict() for item in takeoff.items],
            "totals": takeoff.total_by_item()
        }
        out_p = Path(output_json)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return data

    # Default DXF pipeline
    parser = DXFParser()
    parsed = parser.parse_file(path)

    # Openings
    openings = [
        Opening(
            id=f"OP-{i+1}",
            opening_type=OpeningType.DOOR,
            width_m=0.90,
            location=b.location,
            tag="D1"
        )
        for i, b in enumerate(parsed.blocks)
    ]

    # Walls & Rooms
    wall_segments = parsed.get_segments_by_category(LayerCategory.WALL, parser.layer_profile)
    solver = RoomBoundarySolver()
    rooms = solver.solve_rooms(wall_segments, parsed.texts, door_openings=openings)

    # Takeoff
    rule_engine = QSRuleEngine()
    takeoff = rule_engine.calculate_takeoff(
        drawing_id="DRW-001",
        drawing_number="A-101",
        revision="03",
        rooms=rooms,
        openings=openings,
        blocks=parsed.blocks
    )

    data = {
        "drawing": {
            "filename": parsed.filename,
            "drawing_number": "A-101",
            "revision": "03",
            "units": parsed.drawing_units,
            "scale_to_mm": parsed.scale_to_mm
        },
        "layers": sorted(list(parsed.layers)),
        "segments": [
            {
                "x1": round(s.start.x, 2),
                "y1": round(s.start.y, 2),
                "x2": round(s.end.x, 2),
                "y2": round(s.end.y, 2),
                "layer": s.layer,
                "handle": s.handle
            }
            for s in parsed.segments
        ],
        "rooms": [
            {
                "id": r.id,
                "name": r.name,
                "net_area_sqm": round(r.net_area_sqm, 2),
                "gross_area_sqm": round(r.gross_area_sqm, 2),
                "perimeter_m": round(r.perimeter_m, 2),
                "confidence": r.confidence,
                "status": r.status.value,
                "polygon": [[round(p.x, 2), round(p.y, 2)] for p in r.polygon.vertices]
            }
            for r in rooms
        ],
        "takeoff": [item.to_dict() for item in takeoff.items],
        "totals": takeoff.total_by_item()
    }

    out_p = Path(output_json)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return data

if __name__ == "__main__":
    dxf_sample = Path("c:/Users/Admin/Downloads/Engine/viewer/sample_office.dxf")
    create_synthetic_office_dxf(dxf_sample)
    out_json = Path("c:/Users/Admin/Downloads/Engine/viewer/sample_data.json")
    generate_viewer_data(dxf_sample, out_json)
    print(f"Generated viewer data at {out_json}")
