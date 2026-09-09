import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from parsers.classifier import DrawingTypeClassifier
from parsers.pdf_vector.extractor import VectorPDFExtractor
from semantics.rooms.boundary_solver import RoomBoundarySolver

pdf_path = Path("C:/Users/Admin/Downloads/BRIDGE WAY-FURNITURE LAYOUT.pdf")
classification = DrawingTypeClassifier.classify_file(pdf_path)
print("Classification:", classification.overall_type, classification.page_count)

extractor = VectorPDFExtractor(user_scale_ratio=100)
parsed = extractor.extract_page(pdf_path, page_number=1)
print("Scale:", parsed.scale.scale_ratio)
print("Segments count:", len(parsed.segments))
print("Texts count:", len(parsed.texts))
print("\n--- ALL TEXTS ---")
for t in parsed.texts:
    print(f"'{t.content}' at ({t.location.x:.1f}, {t.location.y:.1f}), height={t.height_mm:.1f}")

wall_candidates = parsed.get_wall_candidates(wall_detector=extractor.wall_detector)
print("\nWall candidates count:", len(wall_candidates))

solver = RoomBoundarySolver()
rooms = solver.solve_rooms(wall_candidates, parsed.texts)
print("\nRooms solved count:", len(rooms))
for r in rooms:
    print(f"  Room: id={r.id}, name='{r.name}', area={r.area_sqm:.2f} sqm, status={r.status}")
