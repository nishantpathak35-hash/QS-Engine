"""
QS Quantification Engine — FastAPI Application Gateway
Main integration surface for Construct-O-Genie.
Enforces Blueprint Section 5, Section 45 (API Design), and Section 101.
"""

from __future__ import annotations
import os
import uuid
import tempfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse

from apps.api.schemas import (
    HealthResponse,
    DrawingUploadResponse,
    TakeoffResponse,
    ExceptionSchema,
    ResolveExceptionRequest
)
from parsers.classifier import DrawingTypeClassifier, DrawingType
from parsers.dxf.reader import DXFParser
from parsers.dxf.layer_classifier import LayerCategory
from parsers.pdf_vector.extractor import VectorPDFExtractor
from semantics.rooms.boundary_solver import RoomBoundarySolver
from qs.rule_engine import QSRuleEngine
from exports.exporter import QSExporter
from semantics.openings.door_detector import DoorDetector
from core.models.semantics import Opening, OpeningType, Room, WallSegment, EntityStatus
from core.models.takeoff import TakeoffSummary
from core.models.project_profile import ProjectProfile
from core.exception_registry import ExceptionRegistry, ExceptionCode, ExceptionSeverity
from core.exceptions import UnitRequiredError, UnsupportedUnitError, ScaleRequiredError
from pricing.cost_engine import CostEstimationEngine, FitoutGrade

# App Initialization
app = FastAPI(
    title="QS Quantification Engine API",
    description="Deterministic Drawing-to-Quantity API for Construct-O-Genie",
    version="1.0.0"
)

# CORS Middleware for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-Memory Storage & Registries for Engine Jobs
STORAGE_DIR = Path(tempfile.gettempdir()) / "qs_engine_storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
GOLDEN_FILES_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "golden_real_files"

DRAWINGS_DB: dict[str, dict] = {}
TAKEOFF_DB: dict[str, TakeoffSummary] = {}
GEOMETRY_DB: dict[str, dict] = {}
EXCEPTION_REGISTRY = ExceptionRegistry()


from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

VIEWER_DIR = Path(__file__).resolve().parent.parent.parent / "viewer"
if VIEWER_DIR.exists():
    app.mount("/viewer", StaticFiles(directory=str(VIEWER_DIR), html=True), name="viewer")


@app.get("/")
def root():
    """Redirect root to the interactive visual viewer."""
    return RedirectResponse(url="/viewer/")


@app.get("/health", response_model=HealthResponse)
def health_check():
    """System health check and engine capability verification."""
    return HealthResponse()


@app.get("/v1/samples")
def list_sample_drawings():
    """Returns curated list of benchmark interior CAD drawings for immediate visual inspection."""
    if not GOLDEN_FILES_DIR.exists():
        return []

    samples = []
    # Prioritize specialized interior fitout projects (PROJECT_21 to PROJECT_30), then others
    all_files = sorted(GOLDEN_FILES_DIR.glob("*.dxf")) + sorted(GOLDEN_FILES_DIR.glob("*.pdf"))
    interior_projects = [f for f in all_files if any(f"PROJECT_{i:02d}" in f.name for i in range(21, 31))]
    other_projects = [f for f in all_files if f not in interior_projects]

    for p in interior_projects + other_projects:
        fname = p.name
        clean_title = fname.replace(".dxf", "").replace(".pdf", "").replace("_", " ")
        if clean_title.startswith("PROJECT "):
            parts = clean_title.split(" ", 2)
            if len(parts) == 3:
                proj_num, proj_name = parts[1], parts[2].title()
                clean_title = f"Project {proj_num}: {proj_name}"
        samples.append({
            "filename": fname,
            "title": clean_title,
            "format": p.suffix.upper().replace(".", "")
        })
    return samples


@app.post("/v1/samples/{filename}/load", response_model=DrawingUploadResponse)
def load_sample_drawing(filename: str):
    """Loads a golden sample CAD/PDF file directly into storage without manual file upload."""
    sample_path = GOLDEN_FILES_DIR / filename
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail=f"Sample file {filename} not found.")

    drawing_id = f"DRW-{uuid.uuid4().hex[:8].upper()}"
    file_ext = sample_path.suffix
    saved_path = STORAGE_DIR / f"{drawing_id}{file_ext}"

    import shutil
    shutil.copyfile(sample_path, saved_path)

    classification = DrawingTypeClassifier.classify_file(saved_path)

    DRAWINGS_DB[drawing_id] = {
        "id": drawing_id,
        "filename": filename,
        "saved_path": saved_path,
        "drawing_number": filename.replace(file_ext, ""),
        "revision": "01",
        "classification": classification
    }

    return DrawingUploadResponse(
        drawing_id=drawing_id,
        filename=filename,
        file_type=classification.overall_type.value,
        page_count=classification.page_count
    )


@app.post("/v1/drawings/upload", response_model=DrawingUploadResponse)
async def upload_drawing(
    file: UploadFile = File(...),
    drawing_number: str = Form("A-101"),
    revision: str = Form("01")
):
    """Uploads CAD/PDF drawing, verifies file signature, and runs drawing classifier."""
    drawing_id = f"DRW-{uuid.uuid4().hex[:8].upper()}"
    file_ext = Path(file.filename).suffix
    saved_path = STORAGE_DIR / f"{drawing_id}{file_ext}"

    # Write file stream to storage
    contents = await file.read()
    with open(saved_path, "wb") as f:
        f.write(contents)

    # Classify Drawing
    classification = DrawingTypeClassifier.classify_file(saved_path)

    # Store record
    DRAWINGS_DB[drawing_id] = {
        "id": drawing_id,
        "filename": file.filename,
        "saved_path": saved_path,
        "drawing_number": drawing_number,
        "revision": revision,
        "classification": classification
    }

    return DrawingUploadResponse(
        drawing_id=drawing_id,
        filename=file.filename,
        file_type=classification.overall_type.value,
        page_count=classification.page_count
    )


@app.post("/v1/drawings/{drawing_id}/process", response_model=TakeoffResponse)
def process_drawing(
    drawing_id: str,
    scale_override: int | None = None,
    assumed_units: str | None = None,
    project_profile: dict | None = None
):
    """Triggers end-to-end geometry extraction, room solving, and QS rule calculations."""
    if drawing_id not in DRAWINGS_DB:
        raise HTTPException(status_code=404, detail="Drawing not found")

    drawing_info = DRAWINGS_DB[drawing_id]
    file_path = drawing_info["saved_path"]
    classification = drawing_info["classification"]

    # Enforce explicit project profile (never allow uncontrolled nulls)
    if project_profile:
        profile_obj = ProjectProfile.from_dict(project_profile)
    else:
        profile_obj = ProjectProfile.create_strict_default()

    # Extract scale override if provided inside profile dictionary or body
    if scale_override is None and project_profile:
        raw_scale = (
            project_profile.get("scale_override")
            or project_profile.get("scale")
            or (project_profile.get("project_profile", {}).get("scale_override") if isinstance(project_profile.get("project_profile"), dict) else None)
            or (project_profile.get("project_profile", {}).get("scale") if isinstance(project_profile.get("project_profile"), dict) else None)
        )
        if raw_scale is not None:
            try:
                scale_override = int(raw_scale)
            except (ValueError, TypeError):
                pass

    rule_engine = QSRuleEngine()
    solver = RoomBoundarySolver()

    if classification.overall_type == DrawingType.VECTOR_PDF:
        # AI Drawing Intelligence & Scope Classification (Section 5 & 15)
        from vision.ai_drawing_agent import AIDrawingAgent
        ai_insight = AIDrawingAgent.analyze_pdf(file_path, user_scale_override=scale_override)

        # Multi-Page Vector PDF Pipeline
        effective_scale = int(ai_insight.scale_ratio) if ai_insight.scale_ratio else (scale_override or 100)
        extractor = VectorPDFExtractor(user_scale_ratio=effective_scale)
        page_count = extractor.get_page_count(file_path)
        all_rooms: list[Room] = []
        all_wall_segments = []
        all_raw_segments = []
        all_pdf_texts = []
        all_exceptions: list[dict] = []

        if ai_insight.discipline in ("FURNITURE_LAYOUT", "LIGHTING_RCP"):
            # Fast-path for Furniture and RCP / Lighting Layouts: bypass false drywall partition hallucinations
            for p_num in range(1, page_count + 1):
                parsed_pdf = extractor.extract_page(file_path, page_number=p_num)
                all_raw_segments.extend(parsed_pdf.segments)
                all_pdf_texts.extend(parsed_pdf.texts)

            ai_takeoff_items = AIDrawingAgent.generate_takeoff_items(ai_insight, drawing_id, drawing_info["drawing_number"])
            ai_rooms = AIDrawingAgent.generate_semantic_rooms(ai_insight, drawing_id, ai_insight.scale_mm_per_pt)
            all_rooms = ai_rooms

            from semantics.schedules.schedule_parser import DrawingScheduleParser
            schedule_items = DrawingScheduleParser.extract_schedule_items(all_pdf_texts, drawing_id=drawing_id)

            takeoff = rule_engine.calculate_takeoff(
                drawing_id=drawing_id,
                drawing_number=drawing_info["drawing_number"],
                revision=drawing_info["revision"],
                rooms=all_rooms,
                walls=[],
                exceptions=all_exceptions,
                project_profile=profile_obj
            )
            # Suppress false drywall and unassigned raw finishes
            takeoff.items = [it for it in takeoff.items if it.item_code not in ("FL-RAW", "CL-RAW", "PT-RAW", "PT-01")]
            takeoff.items.extend(ai_takeoff_items)
            if schedule_items and not ai_takeoff_items:
                # Deduplicate by item_code
                existing_codes = {it.item_code for it in takeoff.items}
                for s_it in schedule_items:
                    if s_it.item_code not in existing_codes:
                        takeoff.items.append(s_it)
            physical_fixtures = []

            # Reconcile base measurements with takeoff line items
            dr_qty = sum(it.quantity for it in takeoff.items if it.item_code.startswith("DR-"))
            if dr_qty > 0:
                takeoff.base_measurements["total_door_count"] = int(dr_qty)
            
            ws_qty = sum(it.quantity for it in takeoff.items if it.item_code in ("FN-01", "FN-01B") or (it.item_code.startswith("FN-") and "WORKSTATION" in it.description.upper()))
            if ws_qty > 0:
                takeoff.base_measurements["total_workstations"] = int(ws_qty)

            # Ensure sqft and rft are populated in base_measurements
            fl_sqm = takeoff.base_measurements.get("total_floor_area_sqm", 0.0)
            if "total_floor_area_sqft" not in takeoff.base_measurements:
                takeoff.base_measurements["total_floor_area_sqft"] = round(fl_sqm * 10.7639104, 2)
            perim_m = takeoff.base_measurements.get("total_room_perimeter_m", 0.0)
            if "total_room_perimeter_rft" not in takeoff.base_measurements:
                takeoff.base_measurements["total_room_perimeter_rft"] = round(perim_m * 3.28084, 2)

        else:
            # Standard Architectural / Partition PDF Takeoff
            for p_num in range(1, page_count + 1):
                try:
                    parsed_pdf = extractor.extract_page(file_path, page_number=p_num)
                except ScaleRequiredError as e:
                    EXCEPTION_REGISTRY.record_exception(
                        code=ExceptionCode.SCALE_REQUIRED,
                        drawing_id=drawing_id,
                        message=f"Page {p_num}: {str(e)}",
                        severity=ExceptionSeverity.BLOCKING,
                        suggested_action="Specify scale_override (e.g. 100 for 1:100)."
                    )
                    takeoff = TakeoffSummary(
                        drawing_id=drawing_id,
                        drawing_number=drawing_info["drawing_number"],
                        revision=drawing_info["revision"],
                        items=[],
                        exceptions=[e.to_dict() for e in EXCEPTION_REGISTRY.get_pending_exceptions() if e.drawing_id == drawing_id]
                    )
                    TAKEOFF_DB[drawing_id] = takeoff
                    return TakeoffResponse(
                        drawing_id=takeoff.drawing_id,
                        drawing_number=takeoff.drawing_number,
                        revision=takeoff.revision,
                        items=[],
                        totals={},
                        exceptions=takeoff.exceptions
                    )

                wall_candidates = parsed_pdf.get_wall_candidates(wall_detector=extractor.wall_detector)
                all_wall_segments.extend(wall_candidates)
                all_raw_segments.extend(parsed_pdf.segments)
                all_pdf_texts.extend(parsed_pdf.texts)
                page_rooms = solver.solve_rooms(wall_candidates, parsed_pdf.texts)
                for r_idx, r in enumerate(page_rooms):
                    r.id = f"P{p_num:02d}-R-{r_idx+1:03d}"
                    r.drawing_id = drawing_id
                    r.page_number = p_num
                    r.page_scale = parsed_pdf.scale.scale_ratio
                all_rooms.extend(page_rooms)
                all_exceptions.extend([e if isinstance(e, dict) else e.to_dict() for e in solver.exceptions])

            semantic_pdf_walls: list[WallSegment] = []
            detected_paired_walls = extractor.wall_detector.detect_walls(all_wall_segments)
            for idx, w in enumerate(detected_paired_walls):
                if w.classification == "partition" and w.length_m >= 1.0:
                    wall_h = None
                    h_src = None
                    if profile_obj and profile_obj.is_assumption_approved("default_ceiling_height_m"):
                        wall_h = profile_obj.get_approved_dimension("default_ceiling_height_m")
                        h_src = "PROJECT_ASSUMPTION"
                    elif profile_obj and profile_obj.allow_assumptions and profile_obj.ceiling_height_m:
                        wall_h = profile_obj.ceiling_height_m
                        h_src = "PROJECT_ASSUMPTION"

                    w.id = f"WALL-PDF-{idx+1:03d}"
                    w.height_m = wall_h
                    w.height_source = h_src
                    w.partition_type = "gypsum"
                    w.status = EntityStatus.REVIEW_REQUIRED if h_src == "PROJECT_ASSUMPTION" else EntityStatus.AUTO_MEASURED
                    semantic_pdf_walls.append(w)

            takeoff = rule_engine.calculate_takeoff(
                drawing_id=drawing_id,
                drawing_number=drawing_info["drawing_number"],
                revision=drawing_info["revision"],
                rooms=all_rooms,
                walls=semantic_pdf_walls,
                exceptions=all_exceptions,
                project_profile=profile_obj
            )

            # Physical Vector Fixture Detection & Legend Cross-Audit (Module 12)
            from semantics.symbols.physical_fixture_detector import PhysicalFixtureDetector
            from semantics.schedules.schedule_parser import DrawingScheduleParser

            physical_fixtures = PhysicalFixtureDetector.detect_fixtures_from_pdf(
                file_path,
                rooms=all_rooms,
                scale_ratio=scale_override or 100.0
            )
            legend_items = DrawingScheduleParser.extract_schedule_items(all_pdf_texts, drawing_id=drawing_id)

            if physical_fixtures:
                takeoff_fixture_items = PhysicalFixtureDetector.generate_takeoff_line_items(
                    physical_fixtures,
                    legend_items=legend_items,
                    project_profile=profile_obj
                )
                takeoff.items.extend(takeoff_fixture_items)
            elif legend_items:
                if profile_obj:
                    for leg in legend_items:
                        leg.wastage_percent = profile_obj.get_wastage_percent(leg.item_code, leg.description)
                takeoff.items.extend(legend_items)

        # Persist geometry and AI insights for visual canvas rendering
        GEOMETRY_DB[drawing_id] = {
            "rooms": all_rooms,
            "walls": all_raw_segments if all_raw_segments else all_wall_segments,
            "openings": [],
            "fixtures": physical_fixtures,
            "ai_insight": {
                "discipline": ai_insight.discipline,
                "title": ai_insight.title,
                "confidence": ai_insight.confidence,
                "scale_ratio": ai_insight.scale_ratio,
                "scale_mm_per_pt": ai_insight.scale_mm_per_pt,
                "reasons": ai_insight.reasons,
                "suppressed_trades": ai_insight.suppressed_trades,
                "ai_provider_used": ai_insight.ai_provider_used
            }
        }


    elif classification.overall_type in (DrawingType.RASTER_PDF, DrawingType.IMAGE):
        raise HTTPException(
            status_code=400,
            detail="Drawing is a raster/scanned image. RASTER_PROCESSING_NOT_SUPPORTED. True raster pipeline pending Sprint 5."
        )
    else:
        # DXF Pipeline
        parser = DXFParser()
        try:
            parsed_dxf = parser.parse_file(file_path, assumed_units=assumed_units)
        except UnitRequiredError as e:
            EXCEPTION_REGISTRY.record_exception(
                code=ExceptionCode.UNIT_REQUIRED,
                drawing_id=drawing_id,
                message=str(e),
                severity=ExceptionSeverity.BLOCKING,
                suggested_action="Specify assumed_units (e.g. 'mm', 'm', 'inches') or calibrate scale."
            )
            takeoff = TakeoffSummary(
                drawing_id=drawing_id,
                drawing_number=drawing_info["drawing_number"],
                revision=drawing_info["revision"],
                items=[],
                exceptions=[e.to_dict() for e in EXCEPTION_REGISTRY.get_pending_exceptions() if e.drawing_id == drawing_id]
            )
            TAKEOFF_DB[drawing_id] = takeoff
            return TakeoffResponse(
                drawing_id=takeoff.drawing_id,
                drawing_number=takeoff.drawing_number,
                revision=takeoff.revision,
                items=[],
                totals={},
                exceptions=takeoff.exceptions
            )
        except UnsupportedUnitError as e:
            EXCEPTION_REGISTRY.record_exception(
                code=ExceptionCode.UNSUPPORTED_UNIT,
                drawing_id=drawing_id,
                message=str(e),
                severity=ExceptionSeverity.BLOCKING,
                suggested_action="Convert drawing units to mm, cm, m, inches, or feet."
            )
            takeoff = TakeoffSummary(
                drawing_id=drawing_id,
                drawing_number=drawing_info["drawing_number"],
                revision=drawing_info["revision"],
                items=[],
                exceptions=[e.to_dict() for e in EXCEPTION_REGISTRY.get_pending_exceptions() if e.drawing_id == drawing_id]
            )
            TAKEOFF_DB[drawing_id] = takeoff
            return TakeoffResponse(
                drawing_id=takeoff.drawing_id,
                drawing_number=takeoff.drawing_number,
                revision=takeoff.revision,
                items=[],
                totals={},
                exceptions=takeoff.exceptions
            )

        wall_segments = parsed_dxf.get_segments_by_category(LayerCategory.WALL, parser.layer_profile)

        # Intelligence-driven block classification & door detection with project profile (Requirement 6)
        door_detector = DoorDetector()
        openings, non_door_blocks, detected_exceptions = door_detector.process_blocks(
            parsed_dxf.blocks, wall_segments, project_profile=profile_obj
        )

        for exc in detected_exceptions:
            EXCEPTION_REGISTRY.record_exception(
                code=ExceptionCode(exc["code"]) if exc["code"] in [c.value for c in ExceptionCode] else ExceptionCode.UNKNOWN_BLOCK,
                drawing_id=drawing_id,
                message=exc["message"],
                severity=ExceptionSeverity(exc.get("severity", "WARNING"))
            )

        rooms = solver.solve_rooms(wall_segments, parsed_dxf.texts, door_openings=openings)

        # Record solver exceptions
        for exc in solver.exceptions:
            EXCEPTION_REGISTRY.record_exception(
                code=ExceptionCode(exc["code"]) if exc["code"] in [c.value for c in ExceptionCode] else ExceptionCode.ROOM_BOUNDARY_OPEN,
                drawing_id=drawing_id,
                message=exc["message"],
                severity=ExceptionSeverity(exc.get("severity", "WARNING"))
            )

        # Convert DXF wall segments to semantic WallSegment entities (Requirement 3)
        semantic_walls: list[WallSegment] = []
        for idx, seg in enumerate(wall_segments):
            layer_name = seg.layer or "A-WALL"
            layer_u = layer_name.upper()
            p_type = "gypsum"
            if "GLASS" in layer_u or "GLZ" in layer_u:
                p_type = "glass"
            elif "BRICK" in layer_u or "BLOCK" in layer_u or "MASON" in layer_u:
                p_type = "masonry"

            wall_h = None
            h_src = None
            if profile_obj and profile_obj.is_assumption_approved("default_ceiling_height_m"):
                wall_h = profile_obj.get_approved_dimension("default_ceiling_height_m")
                h_src = "PROJECT_ASSUMPTION"
            elif profile_obj and profile_obj.allow_assumptions and profile_obj.ceiling_height_m:
                wall_h = profile_obj.ceiling_height_m
                h_src = "PROJECT_ASSUMPTION"

            semantic_walls.append(WallSegment(
                id=seg.handle or f"WALL-{idx+1:03d}",
                start=seg.start,
                end=seg.end,
                thickness_mm=getattr(seg, "thickness_mm", 100.0) or 100.0,
                height_m=wall_h,
                height_source=h_src,
                layer=layer_name,
                classification="partition",
                wall_type="partition",
                partition_type=p_type,
                status=EntityStatus.REVIEW_REQUIRED if h_src == "PROJECT_ASSUMPTION" else EntityStatus.AUTO_MEASURED
            ))

        # Persist geometry for revision matching
        GEOMETRY_DB[drawing_id] = {
            "rooms": rooms,
            "walls": wall_segments,
            "openings": openings
        }

        takeoff = rule_engine.calculate_takeoff(
            drawing_id=drawing_id,
            drawing_number=drawing_info["drawing_number"],
            revision=drawing_info["revision"],
            rooms=rooms,
            openings=openings,
            walls=semantic_walls,
            blocks=parsed_dxf.blocks,
            exceptions=[e.to_dict() for e in EXCEPTION_REGISTRY.get_pending_exceptions() if e.drawing_id == drawing_id],
            assumptions=parsed_dxf.assumptions,
            project_profile=profile_obj
        )

        # Extract schedule items (Lighting fixtures, Electrical, Workstation capacity)
        from semantics.schedules.schedule_parser import DrawingScheduleParser
        schedule_items = DrawingScheduleParser.extract_schedule_items(parsed_dxf.texts, drawing_id=drawing_id)
        if schedule_items:
            takeoff.items.extend(schedule_items)

    # Build geometry payload for visual CAD/PDF rendering
    geom_record = GEOMETRY_DB.get(drawing_id, {})
    render_segments = []
    render_layers = set()
    for s in geom_record.get("walls", []):
        layer_name = getattr(s, "layer", "A-WALL") or "A-WALL"
        render_layers.add(layer_name)
        render_segments.append({
            "x1": round(s.start.x, 2),
            "y1": round(s.start.y, 2),
            "x2": round(s.end.x, 2),
            "y2": round(s.end.y, 2),
            "layer": layer_name,
            "handle": getattr(s, "handle", "")
        })
    for op in geom_record.get("openings", []):
        if op.jamb_p1 and op.jamb_p2:
            render_layers.add("A-DOOR")
            render_segments.append({
                "x1": round(op.jamb_p1.x, 2),
                "y1": round(op.jamb_p1.y, 2),
                "x2": round(op.jamb_p2.x, 2),
                "y2": round(op.jamb_p2.y, 2),
                "layer": "A-DOOR",
                "handle": op.id
            })

    render_rooms = [
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
        for r in geom_record.get("rooms", [])
    ]
    render_fixtures = [
        {
            "id": f.id,
            "item_code": f.item_code,
            "fixture_type": f.fixture_type,
            "description": f.description,
            "category": f.category,
            "x": round(f.location_point.x, 2),
            "y": round(f.location_point.y, 2),
            "room_id": f.room_id,
            "room_name": f.room_name
        }
        for f in geom_record.get("fixtures", [])
    ]
    if render_fixtures:
        render_layers.add("LIGHTING_FIXTURES")

    geometry_payload = {
        "drawing": {
            "filename": drawing_info["filename"],
            "drawing_number": drawing_info["drawing_number"],
            "revision": drawing_info["revision"]
        },
        "layers": sorted(list(render_layers)),
        "segments": render_segments,
        "rooms": render_rooms,
        "fixtures": render_fixtures,
        "ai_insight": geom_record.get("ai_insight", None)
    }

    # Universal Base Measurements Reconciliation for all drawings (DXF, PDF, Schedules)
    if "total_door_count" not in takeoff.base_measurements or takeoff.base_measurements["total_door_count"] == 0:
        dr_qty = sum(it.quantity for it in takeoff.items if it.item_code.startswith("DR-"))
        if dr_qty > 0:
            takeoff.base_measurements["total_door_count"] = int(dr_qty)

    ws_qty = sum(it.quantity for it in takeoff.items if it.item_code in ("FN-01", "FN-01B") or (it.item_code.startswith("FN-") and "WORKSTATION" in it.description.upper()))
    if ws_qty > 0:
        takeoff.base_measurements["total_workstations"] = int(ws_qty)

    fl_sqm = takeoff.base_measurements.get("total_floor_area_sqm", 0.0)
    if not fl_sqm:
        fl_sqm = sum(it.quantity for it in takeoff.items if it.item_code.startswith("FL-") and getattr(it.unit, "value", str(it.unit)).lower() in ("sqm", "m2"))
        if fl_sqm > 0:
            takeoff.base_measurements["total_floor_area_sqm"] = round(fl_sqm, 2)
    takeoff.base_measurements["total_floor_area_sqft"] = round(float(takeoff.base_measurements.get("total_floor_area_sqm", 0.0)) * 10.7639104, 2)

    perim_m = takeoff.base_measurements.get("total_room_perimeter_m", 0.0)
    takeoff.base_measurements["total_room_perimeter_rft"] = round(float(perim_m) * 3.28084, 2)

    TAKEOFF_DB[drawing_id] = takeoff
    estimate = CostEstimationEngine.estimate_project_cost(takeoff, fitout_grade=FitoutGrade.STANDARD)

    return TakeoffResponse(
        drawing_id=takeoff.drawing_id,
        drawing_number=takeoff.drawing_number,
        revision=takeoff.revision,
        items=[item.to_dict() for item in takeoff.items],
        totals=takeoff.total_by_item(),
        exceptions=takeoff.exceptions,
        base_measurements=takeoff.base_measurements,
        geometry=geometry_payload,
        priced_estimate=estimate.to_dict()
    )


@app.get("/v1/drawings/{drawing_id}/quantities", response_model=TakeoffResponse)
def get_quantities(drawing_id: str):
    """Retrieves verified takeoff quantities and formula lineages."""
    if drawing_id not in TAKEOFF_DB:
        raise HTTPException(status_code=404, detail="Takeoff not calculated yet. Call /process first.")

    takeoff = TAKEOFF_DB[drawing_id]
    estimate = CostEstimationEngine.estimate_project_cost(takeoff, fitout_grade=FitoutGrade.STANDARD)
    return TakeoffResponse(
        drawing_id=takeoff.drawing_id,
        drawing_number=takeoff.drawing_number,
        revision=takeoff.revision,
        items=[item.to_dict() for item in takeoff.items],
        totals=takeoff.total_by_item(),
        exceptions=takeoff.exceptions,
        base_measurements=takeoff.base_measurements,
        priced_estimate=estimate.to_dict()
    )


@app.get("/v1/drawings/{drawing_id}/pricing")
def get_pricing(drawing_id: str, fitout_grade: str = "standard"):
    """Calculates priced BOQ, trade distributions, and grand budget totals with selectable fitout grade."""
    if drawing_id not in TAKEOFF_DB:
        raise HTTPException(status_code=404, detail="Takeoff not calculated yet. Call /process first.")

    takeoff = TAKEOFF_DB[drawing_id]
    grade_enum = FitoutGrade.STANDARD
    if fitout_grade.lower() in ("economy", "value"):
        grade_enum = FitoutGrade.ECONOMY
    elif fitout_grade.lower() in ("luxury", "grade_a", "grade-a"):
        grade_enum = FitoutGrade.GRADE_A_LUXURY

    estimate = CostEstimationEngine.estimate_project_cost(takeoff, fitout_grade=grade_enum)
    return estimate.to_dict()


@app.get("/v1/drawings/{drawing_id}/export")
def export_takeoff(drawing_id: str, format: str = "excel"):
    """Downloads takeoff formatted as excel (.xlsx), csv, or json."""
    if drawing_id not in TAKEOFF_DB:
        raise HTTPException(status_code=404, detail="Takeoff not found")

    takeoff = TAKEOFF_DB[drawing_id]

    if format.lower() == "excel":
        excel_path = STORAGE_DIR / f"{drawing_id}_Takeoff.xlsx"
        QSExporter.export_excel(takeoff, excel_path)
        return FileResponse(
            path=str(excel_path),
            filename=f"{takeoff.drawing_number}_Takeoff.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    elif format.lower() == "csv":
        csv_data = QSExporter.export_csv(takeoff)
        return PlainTextResponse(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={takeoff.drawing_number}_Takeoff.csv"}
        )

    else:
        json_data = QSExporter.export_json(takeoff)
        return Response(content=json_data, media_type="application/json")


@app.post("/v1/exceptions/{exception_id}/resolve")
def resolve_exception(exception_id: str, req: ResolveExceptionRequest):
    """Human-in-the-loop override endpoint to resolve flagged exceptions."""
    for exc in EXCEPTION_REGISTRY.get_all():
        if exc.id == exception_id:
            exc.resolve(value=req.resolution_value, user_id=req.user_id)
            return {"status": "resolved", "exception_id": exception_id, "resolution": req.resolution_value}
    raise HTTPException(status_code=404, detail="Exception record not found")


@app.post("/v1/revisions/compare")
def compare_revisions(baseline_id: str, revised_id: str):
    """Compares two drawing revisions and emits quantity and spatial deltas."""
    if baseline_id not in TAKEOFF_DB:
        raise HTTPException(status_code=404, detail=f"Baseline drawing '{baseline_id}' not found or not processed.")
    if revised_id not in TAKEOFF_DB:
        raise HTTPException(status_code=404, detail=f"Revised drawing '{revised_id}' not found or not processed.")

    base_geom = GEOMETRY_DB.get(baseline_id, {})
    rev_geom = GEOMETRY_DB.get(revised_id, {})

    from revision.difference_engine import RevisionDifferenceEngine
    result = RevisionDifferenceEngine.compare_takeoffs(
        baseline=TAKEOFF_DB[baseline_id],
        revised=TAKEOFF_DB[revised_id],
        baseline_rooms=base_geom.get("rooms", []),
        revised_rooms=rev_geom.get("rooms", [])
    )
    return result.to_dict()
