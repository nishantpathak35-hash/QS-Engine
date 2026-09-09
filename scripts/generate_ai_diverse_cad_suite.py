"""
QS Quantification Engine — Diverse CAD Architectural Benchmark Generator
Creates 5 distinct real CAD DXF files covering diverse architectural typologies:
1. Residential 2BHK
2. Healthcare Clinic / OPD
3. Corporate Tech Suite
4. Retail Flagship Store
5. Industrial Warehouse Office
Uses realistic unstandardized CAD layer names and block definitions to stress-test
the Free LLM classification layer and geometric takeoff engine end-to-end.
"""

from pathlib import Path
import yaml
import ezdxf

OUTPUT_DIR = Path("tests/golden_real_files")


def create_specialized_dxf(
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

    # Create custom blocks for doors
    registered_blocks = set()
    for d in doors_data:
        b_name = d["block_name"]
        if b_name not in registered_blocks:
            w_mm = int(d["width_m"] * 1000.0)
            blk = doc.blocks.new(b_name)
            blk.add_line((0, 0), (w_mm, 0))
            blk.add_arc((0, 0), radius=w_mm, start_angle=0, end_angle=90)
            registered_blocks.add(b_name)

    # Add room walls and text
    for r in rooms_data:
        x, y, w, h = r["x"], r["y"], r["w"], r["h"]
        # Add 4 walls on custom wall layer
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


def build_diverse_suite():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_data = {}

    # 1. Residential 2BHK
    p11_file = "PROJECT_11_RESIDENTIAL_2BHK.dxf"
    p11_rooms = [
        {"name": "LIVING ROOM", "x": 0, "y": 0, "w": 5000, "h": 4000, "finish": "FL-01", "area_sqm": 20.00, "perim_m": 18.00},
        {"name": "MASTER BEDROOM", "x": 5500, "y": 0, "w": 4000, "h": 3500, "finish": "FL-01", "area_sqm": 14.00, "perim_m": 15.00},
        {"name": "KIDS BEDROOM", "x": 10000, "y": 0, "w": 3500, "h": 3000, "finish": "FL-01", "area_sqm": 10.50, "perim_m": 13.00},
        {"name": "KITCHEN", "x": 0, "y": 4500, "w": 3000, "h": 2500, "finish": "FL-02", "area_sqm": 7.50, "perim_m": 11.00},
        {"name": "TOILET", "x": 3500, "y": 4500, "w": 2000, "h": 1500, "finish": "FL-02", "area_sqm": 3.00, "perim_m": 7.00},
    ]
    p11_doors = [
        {"block_name": "MY_DOOR_900_V1", "width_m": 0.9, "x": 2000, "y": 0},
        {"block_name": "MY_DOOR_900_V1", "width_m": 0.9, "x": 7000, "y": 0},
        {"block_name": "MY_DOOR_900_V1", "width_m": 0.9, "x": 11500, "y": 0},
        {"block_name": "MY_DOOR_900_V1", "width_m": 0.9, "x": 1000, "y": 4500},
        {"block_name": "TOILET_DOOR_750", "width_m": 0.75, "x": 4000, "y": 4500},
    ]
    create_specialized_dxf(
        OUTPUT_DIR / p11_file,
        wall_layer="CIVIL_BRICK_WALL",
        door_layer="CUSTOM_DOOR_SWING",
        floor_layer="FLOOR_VITRIFIED_TILES",
        anno_layer="ROOM_TAGS",
        rooms_data=p11_rooms,
        doors_data=p11_doors
    )
    manifest_data[p11_file] = {
        "typology": "Residential 2BHK",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p11_rooms},
            "doors": {"total": len(p11_doors)},
            "flooring": {"FL-01": 44.50, "FL-02": 10.50}
        }
    }

    # 2. Healthcare Clinic / OPD
    p12_file = "PROJECT_12_HEALTHCARE_CLINIC.dxf"
    p12_rooms = [
        {"name": "WAITING LOUNGE", "x": 0, "y": 0, "w": 6000, "h": 5000, "finish": "FL-01", "area_sqm": 30.00, "perim_m": 22.00},
        {"name": "CONSULTATION 1", "x": 6500, "y": 0, "w": 4000, "h": 3500, "finish": "FL-01", "area_sqm": 14.00, "perim_m": 15.00},
        {"name": "CONSULTATION 2", "x": 11000, "y": 0, "w": 4000, "h": 3500, "finish": "FL-01", "area_sqm": 14.00, "perim_m": 15.00},
        {"name": "PROCEDURE OT", "x": 0, "y": 5500, "w": 4500, "h": 3500, "finish": "FL-02", "area_sqm": 15.75, "perim_m": 16.00},
        {"name": "PHARMACY", "x": 5000, "y": 5500, "w": 3000, "h": 3000, "finish": "FL-02", "area_sqm": 9.00, "perim_m": 12.00},
    ]
    p12_doors = [
        {"block_name": "CLINIC_FLUSH_DOOR_1000", "width_m": 1.0, "x": 2500, "y": 0},
        {"block_name": "CLINIC_FLUSH_DOOR_1000", "width_m": 1.0, "x": 8000, "y": 0},
        {"block_name": "CLINIC_FLUSH_DOOR_1000", "width_m": 1.0, "x": 12500, "y": 0},
        {"block_name": "CLINIC_FLUSH_DOOR_1000", "width_m": 1.0, "x": 2000, "y": 5500},
        {"block_name": "PHARMACY_SLIDER_900", "width_m": 0.9, "x": 6000, "y": 5500},
    ]
    create_specialized_dxf(
        OUTPUT_DIR / p12_file,
        wall_layer="PARTITION_LEAD_LINED",
        door_layer="CLINIC_DOOR_LEAF",
        floor_layer="ANTISTATIC_FLOOR",
        anno_layer="CLINIC_TEXT",
        rooms_data=p12_rooms,
        doors_data=p12_doors
    )
    manifest_data[p12_file] = {
        "typology": "Healthcare Clinic / OPD",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p12_rooms},
            "doors": {"total": len(p12_doors)},
            "flooring": {"FL-01": 58.00, "FL-02": 24.75}
        }
    }

    # 3. Corporate Tech Suite
    p13_file = "PROJECT_13_CORPORATE_TECH_SUITE.dxf"
    p13_rooms = [
        {"name": "OPEN WORKSPACE", "x": 0, "y": 0, "w": 8000, "h": 6000, "finish": "FL-01", "area_sqm": 48.00, "perim_m": 28.00},
        {"name": "BOARDROOM", "x": 8500, "y": 0, "w": 6000, "h": 4000, "finish": "FL-02", "area_sqm": 24.00, "perim_m": 20.00},
        {"name": "SERVER ROOM", "x": 8500, "y": 4500, "w": 3000, "h": 3000, "finish": "FL-02", "area_sqm": 9.00, "perim_m": 12.00},
        {"name": "EXECUTIVE CABIN", "x": 0, "y": 6500, "w": 4000, "h": 4000, "finish": "FL-01", "area_sqm": 16.00, "perim_m": 16.00},
    ]
    p13_doors = [
        {"block_name": "GLASS_DOOR_900", "width_m": 0.9, "x": 3500, "y": 0},
        {"block_name": "GLASS_DOOR_900", "width_m": 0.9, "x": 10500, "y": 0},
        {"block_name": "FIRE_SERVER_DOOR_1000", "width_m": 1.0, "x": 9500, "y": 4500},
        {"block_name": "GLASS_DOOR_900", "width_m": 0.9, "x": 1500, "y": 6500},
    ]
    create_specialized_dxf(
        OUTPUT_DIR / p13_file,
        wall_layer="GLAZED_PARTITION_100MM",
        door_layer="DOORS_SINGLE_WOOD",
        floor_layer="CARPET_TILE_FINISH",
        anno_layer="TEXT_NOTES",
        rooms_data=p13_rooms,
        doors_data=p13_doors
    )
    manifest_data[p13_file] = {
        "typology": "Corporate Tech Suite",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p13_rooms},
            "doors": {"total": len(p13_doors)},
            "flooring": {"FL-01": 64.00, "FL-02": 33.00}
        }
    }

    # 4. Retail Flagship Store
    p14_file = "PROJECT_14_RETAIL_FLAGSHIP_STORE.dxf"
    p14_rooms = [
        {"name": "SHOWROOM FLOOR", "x": 0, "y": 0, "w": 10000, "h": 7000, "finish": "FL-01", "area_sqm": 70.00, "perim_m": 34.00},
        {"name": "TRIAL ROOM 1", "x": 10500, "y": 0, "w": 2000, "h": 1800, "finish": "FL-01", "area_sqm": 3.60, "perim_m": 7.60},
        {"name": "TRIAL ROOM 2", "x": 10500, "y": 2000, "w": 2000, "h": 1800, "finish": "FL-01", "area_sqm": 3.60, "perim_m": 7.60},
        {"name": "BILLING COUNTER", "x": 10500, "y": 4000, "w": 4000, "h": 3000, "finish": "FL-02", "area_sqm": 12.00, "perim_m": 14.00},
        {"name": "STOCKROOM", "x": 0, "y": 7500, "w": 5000, "h": 4000, "finish": "FL-02", "area_sqm": 20.00, "perim_m": 18.00},
    ]
    p14_doors = [
        {"block_name": "RT_DOOR_800", "width_m": 0.8, "x": 4500, "y": 0},
        {"block_name": "RT_DOOR_800", "width_m": 0.8, "x": 11000, "y": 0},
        {"block_name": "RT_DOOR_800", "width_m": 0.8, "x": 11000, "y": 2000},
        {"block_name": "RT_DOOR_800", "width_m": 0.8, "x": 12000, "y": 4000},
        {"block_name": "STORAGE_DOOR_900", "width_m": 0.9, "x": 2000, "y": 7500},
    ]
    create_specialized_dxf(
        OUTPUT_DIR / p14_file,
        wall_layer="RETAIL_STORE_WALLS",
        door_layer="FITTING_SWING_DOORS",
        floor_layer="CERAMIC_TILES_600X600",
        anno_layer="STORE_TEXT",
        rooms_data=p14_rooms,
        doors_data=p14_doors
    )
    manifest_data[p14_file] = {
        "typology": "Retail Flagship Store",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p14_rooms},
            "doors": {"total": len(p14_doors)},
            "flooring": {"FL-01": 77.20, "FL-02": 32.00}
        }
    }

    # 5. Industrial Warehouse Office
    p15_file = "PROJECT_15_INDUSTRIAL_WAREHOUSE_OFFICE.dxf"
    p15_rooms = [
        {"name": "DISPATCH OFFICE", "x": 0, "y": 0, "w": 7000, "h": 5000, "finish": "FL-01", "area_sqm": 35.00, "perim_m": 24.00},
        {"name": "SUPERVISOR CABIN", "x": 7500, "y": 0, "w": 4000, "h": 4000, "finish": "FL-01", "area_sqm": 16.00, "perim_m": 16.00},
        {"name": "LOCKER ROOM", "x": 0, "y": 5500, "w": 5000, "h": 3500, "finish": "FL-02", "area_sqm": 17.50, "perim_m": 17.00},
        {"name": "TESTING LAB", "x": 5500, "y": 5500, "w": 5000, "h": 4000, "finish": "FL-02", "area_sqm": 20.00, "perim_m": 18.00},
    ]
    p15_doors = [
        {"block_name": "STEEL_FIRE_EXIT_1000", "width_m": 1.0, "x": 3000, "y": 0},
        {"block_name": "OFFICE_FLUSH_DOOR_900", "width_m": 0.9, "x": 9000, "y": 0},
        {"block_name": "OFFICE_FLUSH_DOOR_900", "width_m": 0.9, "x": 2000, "y": 5500},
        {"block_name": "STEEL_FIRE_EXIT_1000", "width_m": 1.0, "x": 7500, "y": 5500},
    ]
    create_specialized_dxf(
        OUTPUT_DIR / p15_file,
        wall_layer="MASONRY_EXT_WALL",
        door_layer="STEEL_FIRE_DOORS",
        floor_layer="EPOXY_FLOORING",
        anno_layer="TAG_ID",
        rooms_data=p15_rooms,
        doors_data=p15_doors
    )
    manifest_data[p15_file] = {
        "typology": "Industrial Warehouse Office",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p15_rooms},
            "doors": {"total": len(p15_doors)},
            "flooring": {"FL-01": 51.00, "FL-02": 37.50}
        }
    }

    # 6. Hotel Luxury Suite
    p16_file = "PROJECT_16_HOTEL_LUXURY_SUITE.dxf"
    p16_rooms = [
        {"name": "FOYER", "x": 0, "y": 0, "w": 3000, "h": 2500, "finish": "FL-01", "area_sqm": 7.50, "perim_m": 11.00},
        {"name": "LIVING LOUNGE", "x": 3500, "y": 0, "w": 6000, "h": 5000, "finish": "FL-01", "area_sqm": 30.00, "perim_m": 22.00},
        {"name": "MASTER SUITE", "x": 10000, "y": 0, "w": 5500, "h": 4500, "finish": "FL-01", "area_sqm": 24.75, "perim_m": 20.00},
        {"name": "ENSUITE BATH", "x": 10000, "y": 5000, "w": 3500, "h": 3000, "finish": "FL-02", "area_sqm": 10.50, "perim_m": 13.00},
        {"name": "WALK IN CLOSET", "x": 14000, "y": 5000, "w": 3000, "h": 2000, "finish": "FL-02", "area_sqm": 6.00, "perim_m": 10.00},
    ]
    p16_doors = [
        {"block_name": "HOTEL_SUITE_DOOR_1000", "width_m": 1.0, "x": 1000, "y": 0},
        {"block_name": "HOTEL_SUITE_DOOR_1000", "width_m": 1.0, "x": 5500, "y": 0},
        {"block_name": "HOTEL_SUITE_DOOR_1000", "width_m": 1.0, "x": 12000, "y": 0},
        {"block_name": "BATHROOM_DOOR_800", "width_m": 0.8, "x": 11000, "y": 5000},
        {"block_name": "BATHROOM_DOOR_800", "width_m": 0.8, "x": 15000, "y": 5000},
    ]
    create_specialized_dxf(
        OUTPUT_DIR / p16_file,
        wall_layer="WALL_HOTEL_DRYWALL",
        door_layer="HOTEL_DOOR_LEAF",
        floor_layer="MARBLE_FLOOR_TILES",
        anno_layer="ROOM_TAGS",
        rooms_data=p16_rooms,
        doors_data=p16_doors
    )
    manifest_data[p16_file] = {
        "typology": "Hospitality Hotel Suite",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p16_rooms},
            "doors": {"total": len(p16_doors)},
            "flooring": {"FL-01": 62.25, "FL-02": 16.50}
        }
    }

    # 7. Restaurant & Cafe
    p17_file = "PROJECT_17_RESTAURANT_CAFE.dxf"
    p17_rooms = [
        {"name": "DINING HALL", "x": 0, "y": 0, "w": 12000, "h": 8000, "finish": "FL-01", "area_sqm": 96.00, "perim_m": 40.00},
        {"name": "COMMERCIAL KITCHEN", "x": 12500, "y": 0, "w": 7000, "h": 5000, "finish": "FL-02", "area_sqm": 35.00, "perim_m": 24.00},
        {"name": "COCKTAIL BAR", "x": 12500, "y": 5500, "w": 5000, "h": 4000, "finish": "FL-01", "area_sqm": 20.00, "perim_m": 18.00},
        {"name": "COLD STORAGE", "x": 0, "y": 8500, "w": 4000, "h": 3000, "finish": "FL-02", "area_sqm": 12.00, "perim_m": 14.00},
        {"name": "RESTROOM", "x": 4500, "y": 8500, "w": 3000, "h": 2500, "finish": "FL-02", "area_sqm": 7.50, "perim_m": 11.00},
    ]
    p17_doors = [
        {"block_name": "MAIN_ENTRY_DOOR_1000", "width_m": 1.0, "x": 5000, "y": 0},
        {"block_name": "KITCHEN_SWING_DOOR_1000", "width_m": 1.0, "x": 15000, "y": 0},
        {"block_name": "KITCHEN_SWING_DOOR_1000", "width_m": 1.0, "x": 14000, "y": 5500},
        {"block_name": "KITCHEN_SWING_DOOR_1000", "width_m": 1.0, "x": 1500, "y": 8500},
        {"block_name": "RESTROOM_DOOR_800", "width_m": 0.8, "x": 5500, "y": 8500},
    ]
    create_specialized_dxf(
        OUTPUT_DIR / p17_file,
        wall_layer="CAFE_INTERIOR_WALLS",
        door_layer="CAFE_SWING_DOORS",
        floor_layer="RESTO_FLOOR_FINISH",
        anno_layer="TEXT_ANNOTATION",
        rooms_data=p17_rooms,
        doors_data=p17_doors
    )
    manifest_data[p17_file] = {
        "typology": "Restaurant & Cafe",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p17_rooms},
            "doors": {"total": len(p17_doors)},
            "flooring": {"FL-01": 116.00, "FL-02": 54.50}
        }
    }

    # 8. Educational & Research Lab
    p18_file = "PROJECT_18_UNIVERSITY_LAB_COMPLEX.dxf"
    p18_rooms = [
        {"name": "RESEARCH WET LAB", "x": 0, "y": 0, "w": 10000, "h": 6000, "finish": "FL-02", "area_sqm": 60.00, "perim_m": 32.00},
        {"name": "INSTRUMENT PREP", "x": 10500, "y": 0, "w": 5000, "h": 4000, "finish": "FL-02", "area_sqm": 20.00, "perim_m": 18.00},
        {"name": "FACULTY CABIN", "x": 10500, "y": 4500, "w": 4000, "h": 4000, "finish": "FL-01", "area_sqm": 16.00, "perim_m": 16.00},
        {"name": "GRADUATE STUDY", "x": 0, "y": 6500, "w": 6000, "h": 5000, "finish": "FL-01", "area_sqm": 30.00, "perim_m": 22.00},
        {"name": "CHEMICAL STORE", "x": 6500, "y": 6500, "w": 4000, "h": 3000, "finish": "FL-02", "area_sqm": 12.00, "perim_m": 14.00},
    ]
    p18_doors = [
        {"block_name": "LAB_FIRE_DOOR_1000", "width_m": 1.0, "x": 4000, "y": 0},
        {"block_name": "LAB_FIRE_DOOR_1000", "width_m": 1.0, "x": 12000, "y": 0},
        {"block_name": "CABIN_FLUSH_DOOR_900", "width_m": 0.9, "x": 12000, "y": 4500},
        {"block_name": "CABIN_FLUSH_DOOR_900", "width_m": 0.9, "x": 2500, "y": 6500},
        {"block_name": "LAB_FIRE_DOOR_1000", "width_m": 1.0, "x": 8000, "y": 6500},
    ]
    create_specialized_dxf(
        OUTPUT_DIR / p18_file,
        wall_layer="LAB_MASONRY_WALL",
        door_layer="LAB_ACCESS_DOORS",
        floor_layer="CHEMICAL_RESISTANT_FLOOR",
        anno_layer="TAG_NAME",
        rooms_data=p18_rooms,
        doors_data=p18_doors
    )
    manifest_data[p18_file] = {
        "typology": "Educational & Research Lab",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p18_rooms},
            "doors": {"total": len(p18_doors)},
            "flooring": {"FL-01": 46.00, "FL-02": 92.00}
        }
    }

    # 9. Banking & Financial Branch
    p19_file = "PROJECT_19_BANK_BRANCH.dxf"
    p19_rooms = [
        {"name": "BANKING HALL", "x": 0, "y": 0, "w": 9000, "h": 7000, "finish": "FL-01", "area_sqm": 63.00, "perim_m": 32.00},
        {"name": "STRONGROOM VAULT", "x": 9500, "y": 0, "w": 5000, "h": 4000, "finish": "FL-02", "area_sqm": 20.00, "perim_m": 18.00},
        {"name": "BRANCH MANAGER", "x": 9500, "y": 4500, "w": 4000, "h": 4000, "finish": "FL-01", "area_sqm": 16.00, "perim_m": 16.00},
        {"name": "TELLER OPERATIONS", "x": 0, "y": 7500, "w": 6000, "h": 3500, "finish": "FL-02", "area_sqm": 21.00, "perim_m": 19.00},
        {"name": "ATM VESTIBULE", "x": 6500, "y": 7500, "w": 3000, "h": 3000, "finish": "FL-01", "area_sqm": 9.00, "perim_m": 12.00},
    ]
    p19_doors = [
        {"block_name": "BANK_ENTRY_DOOR_1000", "width_m": 1.0, "x": 3500, "y": 0},
        {"block_name": "VAULT_SECURITY_DOOR_1200", "width_m": 1.2, "x": 11500, "y": 0},
        {"block_name": "MANAGER_DOOR_900", "width_m": 0.9, "x": 11000, "y": 4500},
        {"block_name": "BANK_ENTRY_DOOR_1000", "width_m": 1.0, "x": 2500, "y": 7500},
        {"block_name": "ATM_ACCESS_DOOR_900", "width_m": 0.9, "x": 7500, "y": 7500},
    ]
    create_specialized_dxf(
        OUTPUT_DIR / p19_file,
        wall_layer="BANK_SECURE_WALL",
        door_layer="SECURITY_DOOR_LEAF",
        floor_layer="POLISHED_GRANITE_FLOOR",
        anno_layer="BANK_TEXT",
        rooms_data=p19_rooms,
        doors_data=p19_doors
    )
    manifest_data[p19_file] = {
        "typology": "Banking & Financial Branch",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p19_rooms},
            "doors": {"total": len(p19_doors)},
            "flooring": {"FL-01": 88.00, "FL-02": 41.00}
        }
    }

    # 10. Sports & Fitness Facility
    p20_file = "PROJECT_20_GYM_FITNESS_CENTER.dxf"
    p20_rooms = [
        {"name": "CARDIO STRENGTH ARENA", "x": 0, "y": 0, "w": 12000, "h": 7000, "finish": "FL-01", "area_sqm": 84.00, "perim_m": 38.00},
        {"name": "YOGA STUDIO", "x": 12500, "y": 0, "w": 7000, "h": 5000, "finish": "FL-01", "area_sqm": 35.00, "perim_m": 24.00},
        {"name": "LOCKER ROOM", "x": 12500, "y": 5500, "w": 6000, "h": 4000, "finish": "FL-02", "area_sqm": 24.00, "perim_m": 20.00},
        {"name": "SHOWER SUITE", "x": 0, "y": 7500, "w": 4000, "h": 3500, "finish": "FL-02", "area_sqm": 14.00, "perim_m": 15.00},
        {"name": "TRAINER OFFICE", "x": 4500, "y": 7500, "w": 4000, "h": 3000, "finish": "FL-01", "area_sqm": 12.00, "perim_m": 14.00},
    ]
    p20_doors = [
        {"block_name": "GYM_MAIN_DOOR_1500", "width_m": 1.5, "x": 5000, "y": 0},
        {"block_name": "STUDIO_DOOR_900", "width_m": 0.9, "x": 15000, "y": 0},
        {"block_name": "LOCKER_DOOR_800", "width_m": 0.8, "x": 14500, "y": 5500},
        {"block_name": "LOCKER_DOOR_800", "width_m": 0.8, "x": 1500, "y": 7500},
        {"block_name": "STUDIO_DOOR_900", "width_m": 0.9, "x": 6000, "y": 7500},
    ]
    create_specialized_dxf(
        OUTPUT_DIR / p20_file,
        wall_layer="GYM_PARTITION_WALLS",
        door_layer="FITNESS_DOOR_SWINGS",
        floor_layer="RUBBER_CUSHION_FLOOR",
        anno_layer="STUDIO_TAGS",
        rooms_data=p20_rooms,
        doors_data=p20_doors
    )
    manifest_data[p20_file] = {
        "typology": "Sports & Fitness Facility",
        "format": "DXF",
        "verified": {
            "rooms": {r["name"]: {"area_sqm": r["area_sqm"], "perimeter_m": r["perim_m"]} for r in p20_rooms},
            "doors": {"total": len(p20_doors)},
            "flooring": {"FL-01": 131.00, "FL-02": 38.00}
        }
    }

    # Save manifest for test verification
    manifest_path = OUTPUT_DIR / "ai_diverse_cad_manifest.yaml"
    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump({"drawings": manifest_data}, f, default_flow_style=False, sort_keys=False)

    print(f"Successfully generated {len(manifest_data)} diverse architectural CAD drawings & manifest at {manifest_path}")


if __name__ == "__main__":
    build_diverse_suite()

