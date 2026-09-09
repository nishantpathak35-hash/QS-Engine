import sys
from pathlib import Path
sys.path.insert(0, ".")
from vision.ai_drawing_agent import AIDrawingAgent

pdf_path = "C:/Users/Admin/Downloads/BRIDGE WAY-FURNITURE LAYOUT.pdf"
insight = AIDrawingAgent.analyze_pdf(pdf_path)
print("Discipline:", insight.discipline, f"({insight.confidence*100:.1f}%)")
print("Title:", insight.title)
print("Scale:", insight.scale_ratio, f"({insight.scale_mm_per_pt:.2f} mm/pt)")
print("AI Provider:", insight.ai_provider_used)
print("\nReasons:")
for r in insight.reasons:
    print(" -", r)
print("\nSuppressed Trades:")
for st in insight.suppressed_trades:
    print(" [X]", st)
print("\nDetected Entities:")
for code, ent in insight.detected_entities.items():
    print(f" [+] {code}: {ent['quantity']} {ent['unit']} — {ent['description']}")
print("\nSpaces:")
for sp in insight.spaces:
    print(f" [*] {sp['name']}: {sp['area_sqm']} sqm")

takeoff_items = AIDrawingAgent.generate_takeoff_items(insight, "TEST-ID", "DWG-01")
print(f"\nGenerated TakeoffLineItems: {len(takeoff_items)}")
for it in takeoff_items:
    print(f"  Item: {it.item_code} | Qty: {it.quantity} {it.unit.value} | Formula: {it.formula}")

rooms = AIDrawingAgent.generate_semantic_rooms(insight, "TEST-ID", insight.scale_mm_per_pt)
print(f"\nGenerated Rooms: {len(rooms)}")
for r in rooms:
    print(f"  Room: {r.id} | {r.name} | Area: {r.net_area_sqm:.2f} sqm")
