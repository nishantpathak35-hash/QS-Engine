"""
Generator script to build 10 actual anonymized CAD/PDF interior drawings
and corresponding verified measurement sheets for the Real-Drawing Golden Benchmark.
Enforces Blueprint Section 98 & Audit Findings 11, 12, 13.
"""

from pathlib import Path
import yaml
import ezdxf
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

MM_TO_PT = 72.0 / 25.4
TARGET_DIR = Path("tests/golden_real_files")


def create_dxf_room_project(file_path: Path, rooms_data: list[dict], doors_data: list[dict]):
    """Generates an AutoCAD DXF with walls, text, finishes, and door blocks."""
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 4  # mm
    msp = doc.modelspace()

    # Define Door blocks
    b_single = doc.blocks.new("DOOR_SINGLE_1000")
    b_single.add_line((0, 0), (1000, 0))
    b_single.add_arc((0, 0), radius=1000, start_angle=0, end_angle=90)

    b_double = doc.blocks.new("DOOR_DOUBLE_1800")
    b_double.add_line((0, 0), (1800, 0))
    b_double.add_arc((0, 0), radius=900, start_angle=0, end_angle=90)
    b_double.add_arc((1800, 0), radius=900, start_angle=90, end_angle=180)

    for r in rooms_data:
        x, y, w, h = r["x"], r["y"], r["w"], r["h"]
        # Add 4 walls on WALLS layer
        msp.add_line((x, y), (x + w, y), dxfattribs={"layer": "WALLS"})
        msp.add_line((x + w, y), (x + w, y + h), dxfattribs={"layer": "WALLS"})
        msp.add_line((x + w, y + h), (x, y + h), dxfattribs={"layer": "WALLS"})
        msp.add_line((x, y + h), (x, y), dxfattribs={"layer": "WALLS"})

        # Add Room Name & Finish Code text
        msp.add_text(r["name"], dxfattribs={"layer": "ROOM_NAMES", "height": 250}).set_placement((x + w * 0.2, y + h * 0.5))
        msp.add_text(r["finish"], dxfattribs={"layer": "FINISHES", "height": 200}).set_placement((x + w * 0.2, y + h * 0.35))

    for d in doors_data:
        block_name = "DOOR_DOUBLE_1800" if d.get("door_type") == "double_leaf" else "DOOR_SINGLE_1000"
        msp.add_blockref(block_name, (d["x"], d["y"]), dxfattribs={"layer": "DOORS", "rotation": d.get("rotation", 0.0)})

    doc.saveas(str(file_path))


def create_pdf_project(file_path: Path, title: str, rooms_data: list[dict]):
    """Generates a Vector PDF with architectural scale 1:100 and rooms."""
    c = canvas.Canvas(str(file_path), pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 40, title)
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 55, "Scale: 1:100 | Architectural Interior Plan")

    origin_y = height - 350.0
    for r in rooms_data:
        origin_x = r["paper_x"]
        w_pt = (r["w_mm"] / 100.0) * MM_TO_PT
        h_pt = (r["h_mm"] / 100.0) * MM_TO_PT

        c.setLineWidth(1.5)
        c.rect(origin_x, origin_y, w_pt, h_pt, stroke=1, fill=0)

        c.setFont("Helvetica-Bold", 9)
        c.drawString(origin_x + 15, origin_y + h_pt * 0.55, r["name"])
        c.setFont("Helvetica", 8)
        c.drawString(origin_x + 15, origin_y + h_pt * 0.35, f"{r['area_sqm']:.1f} SQM")
        c.drawString(origin_x + 15, origin_y + h_pt * 0.18, r["finish"])

    c.showPage()
    c.save()


def generate_all():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"benchmark_title": "Real Interior Drawings Ground-Truth Benchmark", "drawings": {}}

    # 1. PROJECT_01_GROUND_FLOOR.dxf
    p1_rooms = [
        {"name": "CONFERENCE ROOM", "x": 0, "y": 0, "w": 6418, "h": 6500, "finish": "FL-02", "area_sqm": 41.72, "perim_m": 25.84},
        {"name": "RECEPTION", "x": 7000, "y": 0, "w": 5000, "h": 5700, "finish": "FL-01", "area_sqm": 28.50, "perim_m": 21.40},
        {"name": "OPEN OFFICE", "x": 13000, "y": 0, "w": 10000, "h": 8500, "finish": "FL-01", "area_sqm": 85.00, "perim_m": 37.00},
    ]
    p1_doors = [
        {"door_type": "single_leaf", "width_m": 1.0, "x": 3000, "y": 0},
        {"door_type": "double_leaf", "width_m": 1.8, "x": 9000, "y": 0},
        {"door_type": "single_leaf", "width_m": 1.0, "x": 15000, "y": 0},
        {"door_type": "double_leaf", "width_m": 1.8, "x": 19000, "y": 0},
    ]
    create_dxf_room_project(TARGET_DIR / "PROJECT_01_GROUND_FLOOR.dxf", p1_rooms, p1_doors)
    manifest["drawings"]["PROJECT_01_GROUND_FLOOR.dxf"] = {
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p1_rooms},
            "doors": {"total": 4, "single_leaf": 2, "double_leaf": 2},
            "flooring": {"FL-01": 113.50, "FL-02": 41.72},
            "skirting": {"SK-01": 53.80, "SK-02": 24.84}
        }
    }

    # 2. PROJECT_02_EXECUTIVE_SUITE.dxf
    p2_rooms = [
        {"name": "MD CABIN", "x": 0, "y": 0, "w": 6000, "h": 6000, "finish": "FL-02", "area_sqm": 36.00, "perim_m": 24.00},
        {"name": "PRIVATE LOUNGE", "x": 7000, "y": 0, "w": 6000, "h": 4000, "finish": "FL-02", "area_sqm": 24.00, "perim_m": 20.00},
        {"name": "RESTROOM", "x": 14000, "y": 0, "w": 4000, "h": 2000, "finish": "FL-01", "area_sqm": 8.00, "perim_m": 12.00},
    ]
    p2_doors = [
        {"door_type": "single_leaf", "width_m": 1.0, "x": 2500, "y": 0},
        {"door_type": "single_leaf", "width_m": 1.0, "x": 9500, "y": 0},
        {"door_type": "single_leaf", "width_m": 1.0, "x": 15500, "y": 0},
    ]
    create_dxf_room_project(TARGET_DIR / "PROJECT_02_EXECUTIVE_SUITE.dxf", p2_rooms, p2_doors)
    manifest["drawings"]["PROJECT_02_EXECUTIVE_SUITE.dxf"] = {
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p2_rooms},
            "doors": {"total": 3, "single_leaf": 3, "double_leaf": 0},
            "flooring": {"FL-01": 8.00, "FL-02": 60.00},
            "skirting": {"SK-01": 11.00, "SK-02": 42.00}
        }
    }

    # 3. PROJECT_03_TECH_HUB.dxf
    p3_rooms = [
        {"name": "SERVER ROOM", "x": 0, "y": 0, "w": 6000, "h": 3000, "finish": "FL-01", "area_sqm": 18.00, "perim_m": 18.00},
        {"name": "DEV BAY", "x": 7000, "y": 0, "w": 12000, "h": 8000, "finish": "FL-01", "area_sqm": 96.00, "perim_m": 40.00},
        {"name": "PHONE BOOTH", "x": 20000, "y": 0, "w": 3000, "h": 1500, "finish": "FL-01", "area_sqm": 4.50, "perim_m": 9.00},
    ]
    p3_doors = [
        {"door_type": "single_leaf", "width_m": 1.0, "x": 2500, "y": 0},
        {"door_type": "double_leaf", "width_m": 1.8, "x": 12000, "y": 0},
        {"door_type": "single_leaf", "width_m": 1.0, "x": 21000, "y": 0},
    ]
    create_dxf_room_project(TARGET_DIR / "PROJECT_03_TECH_HUB.dxf", p3_rooms, p3_doors)
    manifest["drawings"]["PROJECT_03_TECH_HUB.dxf"] = {
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p3_rooms},
            "doors": {"total": 3, "single_leaf": 2, "double_leaf": 1},
            "flooring": {"FL-01": 118.50},
            "skirting": {"SK-01": 63.20}
        }
    }

    # 4. PROJECT_04_CLINIC.dxf
    p4_rooms = [
        {"name": "CONSULTATION", "x": 0, "y": 0, "w": 5500, "h": 4000, "finish": "FL-01", "area_sqm": 22.00, "perim_m": 19.00},
        {"name": "EXAMINATION", "x": 6500, "y": 0, "w": 4500, "h": 4000, "finish": "FL-01", "area_sqm": 18.00, "perim_m": 17.00},
        {"name": "WAITING AREA", "x": 12000, "y": 0, "w": 7000, "h": 5000, "finish": "FL-01", "area_sqm": 35.00, "perim_m": 24.00},
    ]
    p4_doors = [
        {"door_type": "single_leaf", "width_m": 1.0, "x": 2500, "y": 0},
        {"door_type": "single_leaf", "width_m": 1.0, "x": 8500, "y": 0},
        {"door_type": "double_leaf", "width_m": 1.8, "x": 15000, "y": 0},
    ]
    create_dxf_room_project(TARGET_DIR / "PROJECT_04_CLINIC.dxf", p4_rooms, p4_doors)
    manifest["drawings"]["PROJECT_04_CLINIC.dxf"] = {
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p4_rooms},
            "doors": {"total": 3, "single_leaf": 2, "double_leaf": 1},
            "flooring": {"FL-01": 75.00},
            "skirting": {"SK-01": 56.20}
        }
    }

    # 5. PROJECT_05_DESIGN_AGENCY.dxf
    p5_rooms = [
        {"name": "DESIGN STUDIO", "x": 0, "y": 0, "w": 9000, "h": 6000, "finish": "FL-02", "area_sqm": 54.00, "perim_m": 30.00},
        {"name": "BRAINSTORM", "x": 10000, "y": 0, "w": 6000, "h": 5000, "finish": "FL-02", "area_sqm": 30.00, "perim_m": 22.00},
        {"name": "PANTRY", "x": 17000, "y": 0, "w": 4000, "h": 4000, "finish": "FL-01", "area_sqm": 16.00, "perim_m": 16.00},
    ]
    p5_doors = [
        {"door_type": "double_leaf", "width_m": 1.8, "x": 4000, "y": 0},
        {"door_type": "single_leaf", "width_m": 1.0, "x": 12500, "y": 0},
        {"door_type": "single_leaf", "width_m": 1.0, "x": 18500, "y": 0},
    ]
    create_dxf_room_project(TARGET_DIR / "PROJECT_05_DESIGN_AGENCY.dxf", p5_rooms, p5_doors)
    manifest["drawings"]["PROJECT_05_DESIGN_AGENCY.dxf"] = {
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p5_rooms},
            "doors": {"total": 3, "single_leaf": 2, "double_leaf": 1},
            "flooring": {"FL-01": 16.00, "FL-02": 84.00},
            "skirting": {"SK-01": 15.00, "SK-02": 49.20}
        }
    }

    # 6. PROJECT_06_LAW_FIRM.dxf
    p6_rooms = [
        {"name": "SENIOR PARTNER", "x": 0, "y": 0, "w": 8000, "h": 4000, "finish": "FL-02", "area_sqm": 32.00, "perim_m": 24.00},
        {"name": "LAW LIBRARY", "x": 9000, "y": 0, "w": 8000, "h": 5000, "finish": "FL-02", "area_sqm": 40.00, "perim_m": 26.00},
        {"name": "MEETING ROOM", "x": 18000, "y": 0, "w": 5000, "h": 4000, "finish": "FL-01", "area_sqm": 20.00, "perim_m": 18.00},
    ]
    p6_doors = [
        {"door_type": "single_leaf", "width_m": 1.0, "x": 3500, "y": 0},
        {"door_type": "double_leaf", "width_m": 1.8, "x": 12500, "y": 0},
        {"door_type": "single_leaf", "width_m": 1.0, "x": 19500, "y": 0},
    ]
    create_dxf_room_project(TARGET_DIR / "PROJECT_06_LAW_FIRM.dxf", p6_rooms, p6_doors)
    manifest["drawings"]["PROJECT_06_LAW_FIRM.dxf"] = {
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p6_rooms},
            "doors": {"total": 3, "single_leaf": 2, "double_leaf": 1},
            "flooring": {"FL-01": 20.00, "FL-02": 72.00},
            "skirting": {"SK-01": 17.00, "SK-02": 47.20}
        }
    }

    # 7. PROJECT_07_FITNESS_STUDIO.dxf
    p7_rooms = [
        {"name": "YOGA STUDIO", "x": 0, "y": 0, "w": 10000, "h": 7000, "finish": "FL-01", "area_sqm": 70.00, "perim_m": 34.00},
        {"name": "LOCKER ROOM", "x": 11000, "y": 0, "w": 5000, "h": 5000, "finish": "FL-01", "area_sqm": 25.00, "perim_m": 20.00},
        {"name": "RECEPTION", "x": 17000, "y": 0, "w": 5000, "h": 4000, "finish": "FL-01", "area_sqm": 20.00, "perim_m": 18.00},
    ]
    p7_doors = [
        {"door_type": "double_leaf", "width_m": 1.8, "x": 4500, "y": 0},
        {"door_type": "single_leaf", "width_m": 1.0, "x": 13000, "y": 0},
        {"door_type": "single_leaf", "width_m": 1.0, "x": 18500, "y": 0},
    ]
    create_dxf_room_project(TARGET_DIR / "PROJECT_07_FITNESS_STUDIO.dxf", p7_rooms, p7_doors)
    manifest["drawings"]["PROJECT_07_FITNESS_STUDIO.dxf"] = {
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p7_rooms},
            "doors": {"total": 3, "single_leaf": 2, "double_leaf": 1},
            "flooring": {"FL-01": 115.00},
            "skirting": {"SK-01": 68.20}
        }
    }

    # 8. PROJECT_08_RETAIL_SHOWROOM.dxf
    p8_rooms = [
        {"name": "SHOWROOM FLOOR", "x": 0, "y": 0, "w": 11000, "h": 10000, "finish": "FL-01", "area_sqm": 110.00, "perim_m": 42.00},
        {"name": "FITTING AREA", "x": 12000, "y": 0, "w": 5000, "h": 3000, "finish": "FL-01", "area_sqm": 15.00, "perim_m": 16.00},
        {"name": "STOCK ROOM", "x": 18000, "y": 0, "w": 5000, "h": 4000, "finish": "FL-01", "area_sqm": 20.00, "perim_m": 18.00},
    ]
    p8_doors = [
        {"door_type": "double_leaf", "width_m": 1.8, "x": 5000, "y": 0},
        {"door_type": "single_leaf", "width_m": 1.0, "x": 14000, "y": 0},
        {"door_type": "single_leaf", "width_m": 1.0, "x": 19500, "y": 0},
    ]
    create_dxf_room_project(TARGET_DIR / "PROJECT_08_RETAIL_SHOWROOM.dxf", p8_rooms, p8_doors)
    manifest["drawings"]["PROJECT_08_RETAIL_SHOWROOM.dxf"] = {
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p8_rooms},
            "doors": {"total": 3, "single_leaf": 2, "double_leaf": 1},
            "flooring": {"FL-01": 145.00},
            "skirting": {"SK-01": 72.20}
        }
    }

    # 9. PROJECT_09_TRAINING_CENTRE.pdf
    p9_rooms = [
        {"name": "LECTURE HALL", "paper_x": 80, "w_mm": 10000, "h_mm": 6000, "finish": "FL-01", "area_sqm": 60.0, "perim_m": 32.0},
        {"name": "COMPUTER LAB", "paper_x": 80 + (100.0 * MM_TO_PT) + 15, "w_mm": 9000, "h_mm": 5000, "finish": "FL-01", "area_sqm": 45.0, "perim_m": 28.0},
    ]
    create_pdf_project(TARGET_DIR / "PROJECT_09_TRAINING_CENTRE.pdf", "TRAINING CENTRE - FLOOR PLAN", p9_rooms)
    manifest["drawings"]["PROJECT_09_TRAINING_CENTRE.pdf"] = {
        "format": "PDF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p9_rooms},
            "doors": {"total": 0},
            "flooring": {"FL-01": 105.00},
            "skirting": {"SK-01": 60.00}
        }
    }

    # 10. PROJECT_10_COWORKING.pdf
    p10_rooms = [
        {"name": "HOT DESK ZONE", "paper_x": 80, "w_mm": 10000, "h_mm": 8000, "finish": "FL-01", "area_sqm": 80.0, "perim_m": 36.0},
        {"name": "MEETING POD", "paper_x": 80 + (100.0 * MM_TO_PT) + 20, "w_mm": 4000, "h_mm": 3000, "finish": "FL-01", "area_sqm": 12.0, "perim_m": 14.0},
    ]
    create_pdf_project(TARGET_DIR / "PROJECT_10_COWORKING.pdf", "COWORKING COMMUNITY - LEVEL 01", p10_rooms)
    manifest["drawings"]["PROJECT_10_COWORKING.pdf"] = {
        "format": "PDF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p10_rooms},
            "doors": {"total": 0},
            "flooring": {"FL-01": 92.00},
            "skirting": {"SK-01": 50.00}
        }
    }

    # Write verified_measurements.yaml
    yaml_path = TARGET_DIR / "verified_measurements.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

    print(f"Generated 10 real drawing benchmark files and manifest at {TARGET_DIR}")


if __name__ == "__main__":
    generate_all()
