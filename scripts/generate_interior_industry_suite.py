"""
QS Quantification Engine — Specialized Interior Industry CAD Benchmark Suite
Generates 10 high-specification commercial & residential interior fit-out CAD (.dxf) drawings:
- PROJECT_21: Luxury Penthouse Residence (Italian Marble, Hardwood, Gypsum Partitions)
- PROJECT_22: Coworking Innovation Hub (Carpet Tiles, Acoustic Glass Partitions)
- PROJECT_23: Dermatology & Wellness Clinic (Seamless Antibacterial Vinyl, Sealed Sliders)
- PROJECT_24: Boutique Luxury Hotel Lobby (Grand Entrance Foyer, Timber Studs)
- PROJECT_25: High-Street Fashion Boutique (Polished Concrete, Minimalist Pocket Doors)
- PROJECT_26: Fine Dining Lounge & Bar (Parquet Flooring, Acoustic Gypsum Walls)
- PROJECT_27: Multispecialty Dental Surgery (Static Dissipative Flooring, Sealed Sliders)
- PROJECT_28: Law Chambers & Partners Office (Wool Carpet, Solid Wood Framed Doors)
- PROJECT_29: Modular Kitchen & Wardrobe Studio (Porcelain Slabs, Pocket Doors)
- PROJECT_30: Recording & Podcast Studio (Floating Floor, Staggered Stud Acoustic Walls)
Enforces statutory IS 1200 / POMI / CPWD measurement criteria for the Interior Industry.
"""

from pathlib import Path
import yaml
import ezdxf

OUTPUT_DIR = Path("tests/golden_real_files")


def create_interior_project(
    file_path: Path,
    wall_layer: str,
    door_layer: str,
    floor_layer: str,
    anno_layer: str,
    rooms_data: list[dict],
    doors_data: list[dict]
):
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 4  # mm
    msp = doc.modelspace()

    # Register door blocks with precise leaf geometry
    registered = set()
    for d in doors_data:
        b_name = d["block_name"]
        if b_name not in registered:
            w_mm = int(d["width_m"] * 1000.0)
            blk = doc.blocks.new(b_name)
            blk.add_line((0, 0), (w_mm, 0))
            blk.add_arc((0, 0), radius=w_mm, start_angle=0, end_angle=90)
            registered.add(b_name)

    # Add interior walls and text
    for r in rooms_data:
        x, y, w, h = r["x"], r["y"], r["w"], r["h"]
        # Add 4 walls on specified wall layer
        msp.add_line((x, y), (x + w, y), dxfattribs={"layer": wall_layer})
        msp.add_line((x + w, y), (x + w, y + h), dxfattribs={"layer": wall_layer})
        msp.add_line((x + w, y + h), (x, y + h), dxfattribs={"layer": wall_layer})
        msp.add_line((x, y + h), (x, y), dxfattribs={"layer": wall_layer})

        # Add Room Name & Finish Code text
        msp.add_text(r["name"], dxfattribs={"layer": anno_layer, "height": 250}).set_placement((x + w * 0.2, y + h * 0.5))
        msp.add_text(r["finish"], dxfattribs={"layer": floor_layer, "height": 200}).set_placement((x + w * 0.2, y + h * 0.35))

    # Add door block references
    for d in doors_data:
        msp.add_blockref(
            d["block_name"],
            (d["x"], d["y"]),
            dxfattribs={"layer": door_layer, "rotation": d.get("rotation", 0.0)}
        )

    doc.saveas(str(file_path))


def build_interior_suite():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing manifest if present to preserve Projects 11-20
    manifest_path = OUTPUT_DIR / "ai_diverse_cad_manifest.yaml"
    existing_data = {}
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            existing_data = yaml.safe_load(f).get("drawings", {})

    interior_projects = {}

    # 1. Luxury Penthouse Residence
    p21_file = "PROJECT_21_LUXURY_PENTHOUSE_RESIDENCE.dxf"
    p21_rooms = [
        {"name": "FORMAL LIVING", "x": 0, "y": 0, "w": 7000, "h": 5000, "finish": "FL-01", "area_sqm": 35.00, "perim_m": 24.00},
        {"name": "DINING LOUNGE", "x": 7500, "y": 0, "w": 5000, "h": 4000, "finish": "FL-01", "area_sqm": 20.00, "perim_m": 18.00},
        {"name": "MASTER BEDROOM", "x": 13000, "y": 0, "w": 6000, "h": 4500, "finish": "FL-02", "area_sqm": 27.00, "perim_m": 21.00},
        {"name": "WALK IN CLOSET", "x": 13000, "y": 5000, "w": 3500, "h": 3000, "finish": "FL-02", "area_sqm": 10.50, "perim_m": 13.00},
        {"name": "POWDER TOILET", "x": 17000, "y": 5000, "w": 2500, "h": 2000, "finish": "FL-03", "area_sqm": 5.00, "perim_m": 9.00},
    ]
    p21_doors = [
        {"block_name": "INT_FLUSH_DOOR_900", "width_m": 0.9, "x": 3000, "y": 0},
        {"block_name": "INT_FLUSH_DOOR_900", "width_m": 0.9, "x": 9500, "y": 0},
        {"block_name": "INT_FLUSH_DOOR_900", "width_m": 0.9, "x": 15000, "y": 0},
        {"block_name": "INT_POCKET_DOOR_800", "width_m": 0.8, "x": 14000, "y": 5000},
        {"block_name": "INT_POCKET_DOOR_800", "width_m": 0.8, "x": 18000, "y": 5000},
    ]
    create_interior_project(
        OUTPUT_DIR / p21_file,
        wall_layer="INT_WALL_DRYWALL_100",
        door_layer="INT_FLUSH_DOOR_LEAF",
        floor_layer="FLOOR_FINISH_CODE",
        anno_layer="ROOM_TAGS",
        rooms_data=p21_rooms,
        doors_data=p21_doors
    )
    interior_projects[p21_file] = {
        "typology": "Luxury Residential Penthouse",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p21_rooms},
            "doors": {"total": len(p21_doors)},
            "flooring": {"FL-01": 55.00, "FL-02": 37.50, "FL-03": 5.00}
        }
    }

    # 2. Coworking Innovation Hub
    p22_file = "PROJECT_22_COWORKING_INNOVATION_HUB.dxf"
    p22_rooms = [
        {"name": "OPEN WORKSPACE", "x": 0, "y": 0, "w": 10000, "h": 8000, "finish": "FL-02", "area_sqm": 80.00, "perim_m": 36.00},
        {"name": "EXECUTIVE CABIN 1", "x": 10500, "y": 0, "w": 4000, "h": 4000, "finish": "FL-02", "area_sqm": 16.00, "perim_m": 16.00},
        {"name": "EXECUTIVE CABIN 2", "x": 10500, "y": 4500, "w": 4000, "h": 4000, "finish": "FL-02", "area_sqm": 16.00, "perim_m": 16.00},
        {"name": "CONFERENCE BOARDROOM", "x": 0, "y": 8500, "w": 6000, "h": 5000, "finish": "FL-02", "area_sqm": 30.00, "perim_m": 22.00},
        {"name": "PANTRY CAFE", "x": 6500, "y": 8500, "w": 5000, "h": 4000, "finish": "FL-01", "area_sqm": 20.00, "perim_m": 18.00},
    ]
    p22_doors = [
        {"block_name": "GLASS_DOOR_1000", "width_m": 1.0, "x": 4500, "y": 0},
        {"block_name": "GLASS_DOOR_1000", "width_m": 1.0, "x": 12000, "y": 0},
        {"block_name": "GLASS_DOOR_1000", "width_m": 1.0, "x": 12000, "y": 4500},
        {"block_name": "GLASS_DOOR_1000", "width_m": 1.0, "x": 2500, "y": 8500},
        {"block_name": "INT_FLUSH_DOOR_900", "width_m": 0.9, "x": 8000, "y": 8500},
    ]
    create_interior_project(
        OUTPUT_DIR / p22_file,
        wall_layer="INT_GLASS_PARTITION_WALL",
        door_layer="INT_GLASS_DOORS",
        floor_layer="FLOOR_SPEC",
        anno_layer="SPACE_NAME",
        rooms_data=p22_rooms,
        doors_data=p22_doors
    )
    interior_projects[p22_file] = {
        "typology": "Coworking Innovation Hub",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p22_rooms},
            "doors": {"total": len(p22_doors)},
            "flooring": {"FL-01": 20.00, "FL-02": 142.00}
        }
    }

    # 3. Dermatology & Wellness Clinic
    p23_file = "PROJECT_23_DERMATOLOGY_WELLNESS_CLINIC.dxf"
    p23_rooms = [
        {"name": "RECEPTION LOBBY", "x": 0, "y": 0, "w": 6000, "h": 5000, "finish": "FL-01", "area_sqm": 30.00, "perim_m": 22.00},
        {"name": "CONSULTATION ROOM", "x": 6500, "y": 0, "w": 4500, "h": 4000, "finish": "FL-03", "area_sqm": 18.00, "perim_m": 17.00},
        {"name": "LASER PROCEDURE", "x": 11500, "y": 0, "w": 4500, "h": 3500, "finish": "FL-03", "area_sqm": 15.75, "perim_m": 16.00},
        {"name": "RECOVERY SUITE", "x": 0, "y": 5500, "w": 4000, "h": 3500, "finish": "FL-03", "area_sqm": 14.00, "perim_m": 15.00},
        {"name": "STERILIZATION", "x": 4500, "y": 5500, "w": 3000, "h": 3000, "finish": "FL-03", "area_sqm": 9.00, "perim_m": 12.00},
    ]
    p23_doors = [
        {"block_name": "CLINIC_DOOR_900", "width_m": 0.9, "x": 2500, "y": 0},
        {"block_name": "CLINIC_DOOR_900", "width_m": 0.9, "x": 8000, "y": 0},
        {"block_name": "HERMETIC_SLIDER_1000", "width_m": 1.0, "x": 13000, "y": 0},
        {"block_name": "CLINIC_DOOR_900", "width_m": 0.9, "x": 1500, "y": 5500},
        {"block_name": "HERMETIC_SLIDER_1000", "width_m": 1.0, "x": 5500, "y": 5500},
    ]
    create_interior_project(
        OUTPUT_DIR / p23_file,
        wall_layer="CLINICAL_PARTITION_WALL",
        door_layer="LEAD_LINED_DOORS",
        floor_layer="SEAMLESS_VINYL_FLOOR",
        anno_layer="CLINIC_ANNOTATION",
        rooms_data=p23_rooms,
        doors_data=p23_doors
    )
    interior_projects[p23_file] = {
        "typology": "Dermatology & Wellness Clinic",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p23_rooms},
            "doors": {"total": len(p23_doors)},
            "flooring": {"FL-01": 30.00, "FL-03": 56.75}
        }
    }

    # 4. Boutique Luxury Hotel Lobby
    p24_file = "PROJECT_24_BOUTIQUE_LUXURY_HOTEL_LOBBY.dxf"
    p24_rooms = [
        {"name": "GRAND FOYER", "x": 0, "y": 0, "w": 8000, "h": 6000, "finish": "FL-01", "area_sqm": 48.00, "perim_m": 28.00},
        {"name": "CONCIERGE LOUNGE", "x": 8500, "y": 0, "w": 6000, "h": 5000, "finish": "FL-01", "area_sqm": 30.00, "perim_m": 22.00},
        {"name": "ALL DAY DINING", "x": 15000, "y": 0, "w": 10000, "h": 6000, "finish": "FL-01", "area_sqm": 60.00, "perim_m": 32.00},
        {"name": "PRIVATE MEETING", "x": 0, "y": 6500, "w": 5000, "h": 4000, "finish": "FL-02", "area_sqm": 20.00, "perim_m": 18.00},
        {"name": "RESTROOM", "x": 5500, "y": 6500, "w": 4000, "h": 3000, "finish": "FL-03", "area_sqm": 12.00, "perim_m": 14.00},
    ]
    p24_doors = [
        {"block_name": "DOUBLE_SWING_DOOR_1800", "width_m": 1.8, "x": 3500, "y": 0},
        {"block_name": "INT_FLUSH_DOOR_900", "width_m": 0.9, "x": 11000, "y": 0},
        {"block_name": "DOUBLE_SWING_DOOR_1800", "width_m": 1.8, "x": 19000, "y": 0},
        {"block_name": "INT_FLUSH_DOOR_900", "width_m": 0.9, "x": 2000, "y": 6500},
        {"block_name": "INT_FLUSH_DOOR_900", "width_m": 0.9, "x": 7000, "y": 6500},
    ]
    create_interior_project(
        OUTPUT_DIR / p24_file,
        wall_layer="TIMBER_STUD_PARTITION",
        door_layer="HOTEL_SWING_DOORS",
        floor_layer="MARBLE_FLOOR_SPEC",
        anno_layer="HOTEL_TEXT",
        rooms_data=p24_rooms,
        doors_data=p24_doors
    )
    interior_projects[p24_file] = {
        "typology": "Boutique Hotel Lobby",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p24_rooms},
            "doors": {"total": len(p24_doors)},
            "flooring": {"FL-01": 138.00, "FL-02": 20.00, "FL-03": 12.00}
        }
    }

    # 5. High-Street Fashion Boutique
    p25_file = "PROJECT_25_HIGH_STREET_FASHION_BOUTIQUE.dxf"
    p25_rooms = [
        {"name": "MAIN SHOWROOM", "x": 0, "y": 0, "w": 12000, "h": 7000, "finish": "FL-01", "area_sqm": 84.00, "perim_m": 38.00},
        {"name": "VIP FITTING 1", "x": 12500, "y": 0, "w": 2500, "h": 2000, "finish": "FL-02", "area_sqm": 5.00, "perim_m": 9.00},
        {"name": "VIP FITTING 2", "x": 12500, "y": 2500, "w": 2500, "h": 2000, "finish": "FL-02", "area_sqm": 5.00, "perim_m": 9.00},
        {"name": "TAILORING WORKSHOP", "x": 12500, "y": 5000, "w": 4000, "h": 3500, "finish": "FL-01", "area_sqm": 14.00, "perim_m": 15.00},
        {"name": "STOCK INVENTORY", "x": 0, "y": 7500, "w": 5000, "h": 4000, "finish": "FL-03", "area_sqm": 20.00, "perim_m": 18.00},
    ]
    p25_doors = [
        {"block_name": "STORE_ENTRY_DOOR_1500", "width_m": 1.5, "x": 5000, "y": 0},
        {"block_name": "FITTING_DOOR_800", "width_m": 0.8, "x": 13500, "y": 0},
        {"block_name": "FITTING_DOOR_800", "width_m": 0.8, "x": 13500, "y": 2500},
        {"block_name": "FITTING_DOOR_800", "width_m": 0.8, "x": 14000, "y": 5000},
        {"block_name": "STORE_ENTRY_DOOR_1500", "width_m": 1.5, "x": 2000, "y": 7500},
    ]
    create_interior_project(
        OUTPUT_DIR / p25_file,
        wall_layer="RETAIL_FIXTURE_WALLS",
        door_layer="FITTING_DOOR_SWINGS",
        floor_layer="POLISHED_FLOOR_TILES",
        anno_layer="STORE_LABELS",
        rooms_data=p25_rooms,
        doors_data=p25_doors
    )
    interior_projects[p25_file] = {
        "typology": "High-Street Fashion Boutique",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p25_rooms},
            "doors": {"total": len(p25_doors)},
            "flooring": {"FL-01": 98.00, "FL-02": 10.00, "FL-03": 20.00}
        }
    }

    # 6. Fine Dining Lounge & Bar
    p26_file = "PROJECT_26_FINE_DINING_LOUNGE_BAR.dxf"
    p26_rooms = [
        {"name": "MAIN DINING", "x": 0, "y": 0, "w": 10000, "h": 7000, "finish": "FL-01", "area_sqm": 70.00, "perim_m": 34.00},
        {"name": "PRIVATE DINING PDR", "x": 10500, "y": 0, "w": 5000, "h": 4000, "finish": "FL-02", "area_sqm": 20.00, "perim_m": 18.00},
        {"name": "ISLAND BAR", "x": 10500, "y": 4500, "w": 6000, "h": 4000, "finish": "FL-01", "area_sqm": 24.00, "perim_m": 20.00},
        {"name": "CHEF KITCHEN", "x": 0, "y": 7500, "w": 8000, "h": 5000, "finish": "FL-03", "area_sqm": 40.00, "perim_m": 26.00},
        {"name": "SERVICE CORRIDOR", "x": 10500, "y": 9000, "w": 6000, "h": 2000, "finish": "FL-01", "area_sqm": 12.00, "perim_m": 16.00},
    ]
    p26_doors = [
        {"block_name": "PDR_GLASS_DOOR_1000", "width_m": 1.0, "x": 4500, "y": 0},
        {"block_name": "PDR_GLASS_DOOR_1000", "width_m": 1.0, "x": 12500, "y": 0},
        {"block_name": "PDR_GLASS_DOOR_1000", "width_m": 1.0, "x": 13000, "y": 4500},
        {"block_name": "KITCHEN_DOUBLE_DOOR_1500", "width_m": 1.5, "x": 3000, "y": 7500},
        {"block_name": "PDR_GLASS_DOOR_1000", "width_m": 1.0, "x": 12000, "y": 9000},
    ]
    create_interior_project(
        OUTPUT_DIR / p26_file,
        wall_layer="HEAVY_ACOUSTIC_PARTITION",
        door_layer="KITCHEN_FIRE_DOORS",
        floor_layer="PARQUET_FLOOR_TILES",
        anno_layer="DINING_TEXT",
        rooms_data=p26_rooms,
        doors_data=p26_doors
    )
    interior_projects[p26_file] = {
        "typology": "Fine Dining Lounge & Bar",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p26_rooms},
            "doors": {"total": len(p26_doors)},
            "flooring": {"FL-01": 106.00, "FL-02": 20.00, "FL-03": 40.00}
        }
    }

    # 7. Multispecialty Dental Surgery
    p27_file = "PROJECT_27_MULTISPECIALTY_DENTAL_SURGERY.dxf"
    p27_rooms = [
        {"name": "OPERATORY 1", "x": 0, "y": 0, "w": 4500, "h": 4000, "finish": "FL-03", "area_sqm": 18.00, "perim_m": 17.00},
        {"name": "OPERATORY 2", "x": 5000, "y": 0, "w": 4500, "h": 4000, "finish": "FL-03", "area_sqm": 18.00, "perim_m": 17.00},
        {"name": "XRAY SCANNING", "x": 10000, "y": 0, "w": 3500, "h": 3000, "finish": "FL-03", "area_sqm": 10.50, "perim_m": 13.00},
        {"name": "STERILIZATION LAB", "x": 0, "y": 4500, "w": 3500, "h": 3000, "finish": "FL-03", "area_sqm": 10.50, "perim_m": 13.00},
        {"name": "DOCTORS OFFICE", "x": 4000, "y": 4500, "w": 4000, "h": 3500, "finish": "FL-01", "area_sqm": 14.00, "perim_m": 15.00},
    ]
    p27_doors = [
        {"block_name": "CLINIC_DOOR_900", "width_m": 0.9, "x": 2000, "y": 0},
        {"block_name": "CLINIC_DOOR_900", "width_m": 0.9, "x": 7000, "y": 0},
        {"block_name": "SEALED_SLIDING_DOOR_1000", "width_m": 1.0, "x": 11500, "y": 0},
        {"block_name": "SEALED_SLIDING_DOOR_1000", "width_m": 1.0, "x": 1500, "y": 4500},
        {"block_name": "CLINIC_DOOR_900", "width_m": 0.9, "x": 5500, "y": 4500},
    ]
    create_interior_project(
        OUTPUT_DIR / p27_file,
        wall_layer="SURGICAL_WALL_PARTITION",
        door_layer="SURGERY_ACCESS_DOORS",
        floor_layer="DISP_FLOOR_VINYL",
        anno_layer="CLINIC_MARK",
        rooms_data=p27_rooms,
        doors_data=p27_doors
    )
    interior_projects[p27_file] = {
        "typology": "Multispecialty Dental Surgery",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p27_rooms},
            "doors": {"total": len(p27_doors)},
            "flooring": {"FL-01": 14.00, "FL-03": 57.00}
        }
    }

    # 8. Law Chambers & Partners Office
    p28_file = "PROJECT_28_LAW_CHAMBERS_PARTNERS_OFFICE.dxf"
    p28_rooms = [
        {"name": "SENIOR PARTNER", "x": 0, "y": 0, "w": 6000, "h": 5000, "finish": "FL-02", "area_sqm": 30.00, "perim_m": 22.00},
        {"name": "ASSOCIATE POOL", "x": 6500, "y": 0, "w": 7000, "h": 5000, "finish": "FL-02", "area_sqm": 35.00, "perim_m": 24.00},
        {"name": "LAW LIBRARY", "x": 14000, "y": 0, "w": 6000, "h": 4000, "finish": "FL-01", "area_sqm": 24.00, "perim_m": 20.00},
        {"name": "MEDIATION ROOM", "x": 0, "y": 5500, "w": 5000, "h": 4000, "finish": "FL-02", "area_sqm": 20.00, "perim_m": 18.00},
        {"name": "CLIENT WAITING", "x": 5500, "y": 5500, "w": 4000, "h": 3500, "finish": "FL-01", "area_sqm": 14.00, "perim_m": 15.00},
    ]
    p28_doors = [
        {"block_name": "HEAVY_TIMBER_DOOR_1000", "width_m": 1.0, "x": 2500, "y": 0},
        {"block_name": "ASSOCIATE_DOOR_900", "width_m": 0.9, "x": 9500, "y": 0},
        {"block_name": "HEAVY_TIMBER_DOOR_1000", "width_m": 1.0, "x": 16500, "y": 0},
        {"block_name": "HEAVY_TIMBER_DOOR_1000", "width_m": 1.0, "x": 2000, "y": 5500},
        {"block_name": "ASSOCIATE_DOOR_900", "width_m": 0.9, "x": 7000, "y": 5500},
    ]
    create_interior_project(
        OUTPUT_DIR / p28_file,
        wall_layer="INT_WALL_DRYWALL_100",
        door_layer="SOLID_WOOD_DOORS",
        floor_layer="WOOL_CARPET_TILES",
        anno_layer="CHAMBERS_TAG",
        rooms_data=p28_rooms,
        doors_data=p28_doors
    )
    interior_projects[p28_file] = {
        "typology": "Law Chambers & Partners Office",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p28_rooms},
            "doors": {"total": len(p28_doors)},
            "flooring": {"FL-01": 38.00, "FL-02": 85.00}
        }
    }

    # 9. Modular Kitchen & Wardrobe Studio
    p29_file = "PROJECT_29_MODULAR_KITCHEN_WARDROBE_STUDIO.dxf"
    p29_rooms = [
        {"name": "ISLAND KITCHEN", "x": 0, "y": 0, "w": 6000, "h": 5000, "finish": "FL-01", "area_sqm": 30.00, "perim_m": 22.00},
        {"name": "WARDROBE DISPLAY", "x": 6500, "y": 0, "w": 6000, "h": 4000, "finish": "FL-02", "area_sqm": 24.00, "perim_m": 20.00},
        {"name": "DESIGN CONSULTATION", "x": 13000, "y": 0, "w": 5000, "h": 4000, "finish": "FL-02", "area_sqm": 20.00, "perim_m": 18.00},
        {"name": "MATERIAL GALLERY", "x": 0, "y": 5500, "w": 5000, "h": 4000, "finish": "FL-01", "area_sqm": 20.00, "perim_m": 18.00},
        {"name": "SAMPLE STORAGE", "x": 5500, "y": 5500, "w": 4000, "h": 3000, "finish": "FL-03", "area_sqm": 12.00, "perim_m": 14.00},
    ]
    p29_doors = [
        {"block_name": "GLASS_SLIDING_DOOR_1200", "width_m": 1.2, "x": 2500, "y": 0},
        {"block_name": "FLUSH_POCKET_DOOR_900", "width_m": 0.9, "x": 9000, "y": 0},
        {"block_name": "FLUSH_POCKET_DOOR_900", "width_m": 0.9, "x": 15000, "y": 0},
        {"block_name": "GLASS_SLIDING_DOOR_1200", "width_m": 1.2, "x": 2000, "y": 5500},
        {"block_name": "FLUSH_POCKET_DOOR_900", "width_m": 0.9, "x": 7000, "y": 5500},
    ]
    create_interior_project(
        OUTPUT_DIR / p29_file,
        wall_layer="STUDIO_DISPLAY_WALLS",
        door_layer="STUDIO_SLIDING_DOORS",
        floor_layer="PORCELAIN_TILES_SPEC",
        anno_layer="STUDIO_TEXT",
        rooms_data=p29_rooms,
        doors_data=p29_doors
    )
    interior_projects[p29_file] = {
        "typology": "Modular Kitchen & Wardrobe Studio",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p29_rooms},
            "doors": {"total": len(p29_doors)},
            "flooring": {"FL-01": 50.00, "FL-02": 44.00, "FL-03": 12.00}
        }
    }

    # 10. Recording & Podcast Studio
    p30_file = "PROJECT_30_RECORDING_PODCAST_STUDIO.dxf"
    p30_rooms = [
        {"name": "LIVE SOUND STAGE", "x": 0, "y": 0, "w": 8000, "h": 6000, "finish": "FL-02", "area_sqm": 48.00, "perim_m": 28.00},
        {"name": "CONTROL BOOTH", "x": 8500, "y": 0, "w": 5000, "h": 4000, "finish": "FL-02", "area_sqm": 20.00, "perim_m": 18.00},
        {"name": "SOUND LOCK AIRLOCK", "x": 8500, "y": 4500, "w": 3000, "h": 2000, "finish": "FL-02", "area_sqm": 6.00, "perim_m": 10.00},
        {"name": "PODCAST BOOTH", "x": 0, "y": 6500, "w": 4000, "h": 3000, "finish": "FL-02", "area_sqm": 12.00, "perim_m": 14.00},
        {"name": "CLIENT SCREENING", "x": 4500, "y": 6500, "w": 5000, "h": 4000, "finish": "FL-01", "area_sqm": 20.00, "perim_m": 18.00},
    ]
    p30_doors = [
        {"block_name": "SOUNDPROOF_DOOR_1000", "width_m": 1.0, "x": 3500, "y": 0},
        {"block_name": "SOUNDPROOF_DOOR_1000", "width_m": 1.0, "x": 10500, "y": 0},
        {"block_name": "SOUNDPROOF_DOOR_1000", "width_m": 1.0, "x": 9500, "y": 4500},
        {"block_name": "SOUNDPROOF_DOOR_1000", "width_m": 1.0, "x": 1500, "y": 6500},
        {"block_name": "SOUNDPROOF_DOOR_1000", "width_m": 1.0, "x": 6500, "y": 6500},
    ]
    create_interior_project(
        OUTPUT_DIR / p30_file,
        wall_layer="STAGGERED_STUD_ACOUSTIC_WALL",
        door_layer="ACOUSTIC_SEAL_DOORS",
        floor_layer="FLOATING_FLOOR_TILES",
        anno_layer="AUDIO_TEXT",
        rooms_data=p30_rooms,
        doors_data=p30_doors
    )
    interior_projects[p30_file] = {
        "typology": "Recording & Podcast Studio",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p30_rooms},
            "doors": {"total": len(p30_doors)},
            "flooring": {"FL-01": 20.00, "FL-02": 86.00}
        }
    }

    # Merge with existing drawings
    existing_data.update(interior_projects)

    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump({"drawings": existing_data}, f, default_flow_style=False, sort_keys=False)

    print(f"Successfully generated {len(interior_projects)} specialized interior CAD drawings.")
    print(f"Total active diverse CAD benchmark drawings in manifest: {len(existing_data)}")


if __name__ == "__main__":
    build_interior_suite()
