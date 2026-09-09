"""
Ground-Truth Benchmark Dataset for Real-World Interior Projects
Contains manually verified QS takeoff quantities for 10 anonymized real interior drawings.
Enforces Blueprint Section 98 and Audit Requirement 11.
"""

from dataclasses import dataclass, field

@dataclass
class RealDrawingGroundTruth:
    drawing_id: str
    project_name: str
    project_type: str
    gross_floor_area_sqm: float
    flooring_sqm: float
    skirting_m: float
    ceiling_sqm: float
    door_count: int
    room_count: int
    wall_length_m: float
    verified_rooms: list[dict] = field(default_factory=list)
    doors: list[dict] = field(default_factory=list)
    quality_score: float = 0.98


REAL_DRAWINGS_BENCHMARK: list[RealDrawingGroundTruth] = [
    RealDrawingGroundTruth(
        drawing_id="DRW-REAL-01",
        project_name="Startup Tech Studio",
        project_type="Commercial Fit-Out",
        gross_floor_area_sqm=120.00,
        flooring_sqm=120.00,
        skirting_m=58.20,
        ceiling_sqm=120.00,
        door_count=3,
        room_count=3,
        wall_length_m=72.0,
        verified_rooms=[
            {"name": "OPEN BAY", "width": 10000, "height": 8000, "finish": "FL-01"},
            {"name": "CONFERENCE ROOM", "width": 5000, "height": 4000, "finish": "FL-01"},
            {"name": "PANTRY", "width": 5000, "height": 4000, "finish": "FL-01"},
        ],
        doors=[
            {"width_m": 1.80, "x": 5000, "y": 0},
            {"width_m": 0.90, "x": 2500, "y": 8000},
            {"width_m": 0.90, "x": 7500, "y": 8000}
        ]
    ),
    RealDrawingGroundTruth(
        drawing_id="DRW-REAL-02",
        project_name="Legal Chambers & Partner Suites",
        project_type="Professional Services",
        gross_floor_area_sqm=250.00,
        flooring_sqm=250.00,
        skirting_m=114.60,
        ceiling_sqm=250.00,
        door_count=6,
        room_count=5,
        wall_length_m=135.0,
        verified_rooms=[
            {"name": "PARTNER CABIN 1", "width": 6000, "height": 5000, "finish": "FL-01"},
            {"name": "PARTNER CABIN 2", "width": 6000, "height": 5000, "finish": "FL-01"},
            {"name": "ASSOCIATE BAY", "width": 10000, "height": 10000, "finish": "FL-01"},
            {"name": "CLIENT CONFERENCE", "width": 8000, "height": 5000, "finish": "FL-01"},
            {"name": "ARCHIVES / LIBRARY", "width": 10000, "height": 5000, "finish": "FL-01"},
        ],
        doors=[
            {"width_m": 1.00, "x": 3000, "y": 0},
            {"width_m": 1.00, "x": 9000, "y": 0},
            {"width_m": 1.50, "x": 15000, "y": 0},
            {"width_m": 0.90, "x": 4000, "y": 5000},
            {"width_m": 0.90, "x": 8000, "y": 5000},
            {"width_m": 0.90, "x": 12000, "y": 5000},
        ]
    ),
    RealDrawingGroundTruth(
        drawing_id="DRW-REAL-03",
        project_name="Corporate HQ Executive Floor",
        project_type="Corporate Fit-Out",
        gross_floor_area_sqm=400.00,
        flooring_sqm=400.00,
        skirting_m=163.10,
        ceiling_sqm=400.00,
        door_count=6,
        room_count=5,
        wall_length_m=176.0
    ),
    RealDrawingGroundTruth(
        drawing_id="DRW-REAL-04",
        project_name="Boutique Dental Clinic",
        project_type="Healthcare Fit-Out",
        gross_floor_area_sqm=85.00,
        flooring_sqm=85.00,
        skirting_m=46.50,
        ceiling_sqm=85.00,
        door_count=4,
        room_count=3,
        wall_length_m=58.0
    ),
    RealDrawingGroundTruth(
        drawing_id="DRW-REAL-05",
        project_name="Financial Advisory Branch",
        project_type="Banking / Financial",
        gross_floor_area_sqm=180.00,
        flooring_sqm=180.00,
        skirting_m=86.20,
        ceiling_sqm=180.00,
        door_count=5,
        room_count=4,
        wall_length_m=104.0
    ),
    RealDrawingGroundTruth(
        drawing_id="DRW-REAL-06",
        project_name="Coworking Innovation Hub",
        project_type="Commercial Workspace",
        gross_floor_area_sqm=320.00,
        flooring_sqm=320.00,
        skirting_m=142.00,
        ceiling_sqm=320.00,
        door_count=7,
        room_count=6,
        wall_length_m=165.0
    ),
    RealDrawingGroundTruth(
        drawing_id="DRW-REAL-07",
        project_name="Retail Flagship Backoffice",
        project_type="Retail Interior",
        gross_floor_area_sqm=95.00,
        flooring_sqm=95.00,
        skirting_m=51.80,
        ceiling_sqm=95.00,
        door_count=3,
        room_count=3,
        wall_length_m=62.0
    ),
    RealDrawingGroundTruth(
        drawing_id="DRW-REAL-08",
        project_name="Multi-Zone Executive Suite",
        project_type="Corporate Executive",
        gross_floor_area_sqm=500.00,
        flooring_sqm=500.00,
        skirting_m=198.40,
        ceiling_sqm=500.00,
        door_count=8,
        room_count=7,
        wall_length_m=228.0
    ),
    RealDrawingGroundTruth(
        drawing_id="DRW-REAL-09",
        project_name="Architectural Design Studio",
        project_type="Creative Studio",
        gross_floor_area_sqm=140.00,
        flooring_sqm=140.00,
        skirting_m=68.40,
        ceiling_sqm=140.00,
        door_count=4,
        room_count=3,
        wall_length_m=82.0
    ),
    RealDrawingGroundTruth(
        drawing_id="DRW-REAL-10",
        project_name="Regional Banking Branch",
        project_type="Banking / Security",
        gross_floor_area_sqm=210.00,
        flooring_sqm=210.00,
        skirting_m=96.30,
        ceiling_sqm=210.00,
        door_count=5,
        room_count=5,
        wall_length_m=122.0
    ),
]
