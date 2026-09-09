"""
QS Quantification Engine — Command-Line Takeoff Utility
Enables standalone batch estimation, measurement, and BOQ export.
Usage:
    python -m core.cli path/to/drawing.dxf --export-excel takeoff.xlsx
"""

from __future__ import annotations
import argparse
from pathlib import Path

from parsers.classifier import DrawingClassifier, DrawingType
from parsers.dxf.reader import DXFParser
from parsers.dxf.layer_classifier import LayerCategory
from parsers.pdf_vector.extractor import VectorPDFExtractor
from semantics.rooms.boundary_solver import RoomBoundarySolver
from semantics.openings.door_detector import DoorDetector
from qs.rule_engine import QSRuleEngine
from exports.exporter import MultiFormatExporter

def main():
    parser = argparse.ArgumentParser(description="Construct-O-Genie Standalone QS Engine CLI")
    parser.add_argument("drawing", help="Path to input drawing file (.dxf or .pdf)")
    parser.add_argument("--scale", type=int, default=None, help="User override scale denominator (e.g. 100 for 1:100)")
    parser.add_argument("--assumed-units", default="mm", help="Assumed units if DXF is unitless (default: mm)")
    parser.add_argument("--profile", default=None, help="Path to custom QS rule YAML profile")
    parser.add_argument("--export-excel", default=None, help="Path to export takeoff Excel file (.xlsx)")
    parser.add_argument("--export-csv", default=None, help="Path to export takeoff CSV file (.csv)")
    parser.add_argument("--export-json", default=None, help="Path to export takeoff JSON file (.json)")

    args = parser.parse_args()
    file_path = Path(args.drawing)

    if not file_path.exists():
        print(f"[-] Error: File '{file_path}' not found.")
        return 1

    print(f"[*] Ingesting Drawing: {file_path.name}")
    classifier = DrawingClassifier()
    classification = classifier.classify_file(file_path)
    print(f"[*] Detected Drawing Type: {classification.overall_type.value.upper()}")

    if classification.overall_type == DrawingType.RASTER_IMAGE:
        print("[-] Error: Scanned/Raster image detected. RASTER_PROCESSING_NOT_SUPPORTED. True raster pipeline pending Sprint 5.")
        return 1

    rule_engine = QSRuleEngine(profile_path=args.profile)
    solver = RoomBoundarySolver()

    if classification.overall_type == DrawingType.VECTOR_PDF:
        extractor = VectorPDFExtractor(user_scale_ratio=args.scale)
        parsed = extractor.extract_page(file_path, page_number=1)
        print(f"[*] Scale Calibrated: {parsed.scale.ratio_string} via {parsed.scale.source}")
        rooms = solver.solve_rooms(parsed.segments, parsed.texts)
        takeoff = rule_engine.calculate_takeoff(
            drawing_id=f"DRW-{file_path.stem}",
            drawing_number=file_path.stem,
            revision="01",
            rooms=rooms
        )
    else:
        dxf_parser = DXFParser()
        parsed = dxf_parser.parse_file(file_path, assumed_units=args.assumed_units)
        wall_segments = parsed.get_segments_by_category(LayerCategory.WALL, dxf_parser.layer_profile)

        # Intelligence-driven block classification & door detection
        door_detector = DoorDetector()
        openings, non_doors, exceptions = door_detector.process_blocks(parsed.blocks, wall_segments)
        
        rooms = solver.solve_rooms(wall_segments, parsed.texts, door_openings=openings)
        takeoff = rule_engine.calculate_takeoff(
            drawing_id=f"DRW-{file_path.stem}",
            drawing_number=file_path.stem,
            revision="01",
            rooms=rooms,
            openings=openings,
            blocks=parsed.blocks,
            exceptions=exceptions,
            assumptions=parsed.assumptions
        )

    print(f"[+] Measurement Complete: {len(rooms)} rooms detected, {len(takeoff.items)} line items computed.")
    if takeoff.exceptions:
        print(f"[!] {len(takeoff.exceptions)} exceptions logged (e.g. unknown blocks, review required).")

    # Print Summary to terminal
    totals = takeoff.total_by_item()
    print("\n--- BOQ TOTALS SUMMARY ---")
    for code, data in totals.items():
        print(f"  {code:8} | {data['description']:45} | {data['total_quantity']:>8.2f} {data['unit']:4} ({data['count']} items)")

    exporter = MultiFormatExporter()
    if args.export_excel:
        out = exporter.export_to_excel(takeoff, args.export_excel)
        print(f"[+] Exported formatted Excel BOQ: {out}")
    if args.export_csv:
        out = exporter.export_to_csv(takeoff, args.export_csv)
        print(f"[+] Exported CSV: {out}")
    if args.export_json:
        out = exporter.export_to_json(takeoff, args.export_json)
        print(f"[+] Exported JSON: {out}")

    return 0

if __name__ == "__main__":
    main()
