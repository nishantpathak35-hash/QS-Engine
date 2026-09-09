"""
QS Quantification Engine — Door & Opening Intelligence Layer
Associates classified door blocks/symbols with host wall segments, resolves 
orientation (horizontal, vertical, angled), and synthesizes precise jamb thresholds.
"""

from __future__ import annotations
import math
import re
from typing import Sequence
import shapely.geometry as sg

from core.geometry.primitives import Point2D, Segment2D
from core.models.semantics import Opening, OpeningType, EntityStatus
from core.models.project_profile import ProjectProfile
from parsers.dxf.reader import ExtractedBlock
from parsers.dxf.block_classifier import BlockClassifier, BlockCategory

class DoorDetector:
    """Detects and resolves door openings, pairing them with their host walls."""

    def __init__(
        self,
        classifier: BlockClassifier | None = None,
        max_wall_distance_mm: float = 350.0
    ):
        self.classifier = classifier or BlockClassifier()
        self.max_wall_distance_mm = max_wall_distance_mm

    def process_blocks(
        self,
        blocks: Sequence[ExtractedBlock],
        wall_segments: Sequence[Segment2D],
        project_profile: ProjectProfile | None = None
    ) -> tuple[list[Opening], list[ExtractedBlock], list[dict]]:
        """
        Classifies blocks and resolves doors against host walls.
        
        Returns:
            - resolved_openings: List[Opening]
            - non_door_blocks: List[ExtractedBlock] (furniture, fixtures, etc.)
            - exceptions_to_record: List[dict] (e.g. UNKNOWN_BLOCK, LOW_CONFIDENCE_DOOR)
        """
        openings: list[Opening] = []
        non_doors: list[ExtractedBlock] = []
        exceptions: list[dict] = []

        # Convert wall segments to Shapely LineStrings for spatial distance
        wall_lines = [
            (seg, sg.LineString([seg.start.to_tuple(), seg.end.to_tuple()]))
            for seg in wall_segments
        ]

        # Collect all wall segment endpoints for precise jamb snapping
        wall_endpoints: list[Point2D] = []
        for seg in wall_segments:
            wall_endpoints.append(seg.start)
            wall_endpoints.append(seg.end)

        door_counter = 1

        for block in blocks:
            result = self.classifier.classify(block)

            if result.category == BlockCategory.UNKNOWN:
                exceptions.append({
                    "code": "UNKNOWN_BLOCK",
                    "block_name": block.name,
                    "layer": block.layer,
                    "location": (block.location.x, block.location.y),
                    "message": f"Block '{block.name}' on layer '{block.layer}' is unclassified."
                })
                non_doors.append(block)
                continue

            if not result.is_door:
                non_doors.append(block)
                continue

            # It is a door candidate! Associate with host wall.
            door_pt = sg.Point(block.location.x, block.location.y)
            best_wall = None
            min_dist = float("inf")
            best_line = None

            for seg, line in wall_lines:
                dist = line.distance(door_pt)
                if dist < min_dist and dist <= self.max_wall_distance_mm:
                    min_dist = dist
                    best_wall = seg
                    best_line = line

            # Determine door width
            status = EntityStatus.AUTO_MEASURED
            confidence = result.confidence
            is_provisional = False
            width_source = None

            if result.detected_width_m is not None:
                width_m = result.detected_width_m
                width_source = "DRAWING"
            elif project_profile and (project_profile.is_assumption_approved("default_door_width_m") or project_profile.is_assumption_approved("default_door_width_mm")):
                w_val = project_profile.get_approved_dimension("default_door_width_m")
                if w_val is None:
                    w_mm = project_profile.get_approved_dimension("default_door_width_mm")
                    w_val = (w_mm / 1000.0) if w_mm else None
                width_m = w_val
                width_source = "PROJECT_ASSUMPTION"
                is_provisional = True
                status = EntityStatus.REVIEW_REQUIRED
                confidence = min(confidence, 0.80)
            else:
                exceptions.append({
                    "code": "MISSING_OPENING_WIDTH",
                    "block_name": block.name,
                    "location": (block.location.x, block.location.y),
                    "message": f"Door opening '{block.name}' at ({block.location.x:.1f}, {block.location.y:.1f}) has unknown width. Review required.",
                    "severity": "WARNING"
                })
                width_m = None
                width_source = None
                is_provisional = True
                status = EntityStatus.REVIEW_REQUIRED
                confidence = min(confidence, 0.70)

            # Determine door height
            height_m = None
            height_source = None
            for k, v in block.attributes.items():
                if k.upper() in ("HEIGHT", "DOOR_HEIGHT", "H"):
                    try:
                        h_val = float(re.sub(r"[^\d.]", "", str(v)))
                        height_m = h_val / 1000.0 if h_val > 50.0 else h_val
                        height_source = "DRAWING"
                    except ValueError:
                        pass

            if height_m is None:
                if project_profile and (project_profile.is_assumption_approved("default_door_height_m") or project_profile.is_assumption_approved("default_door_height_mm")):
                    h_val = project_profile.get_approved_dimension("default_door_height_m")
                    if h_val is None:
                        h_mm = project_profile.get_approved_dimension("default_door_height_mm")
                        h_val = (h_mm / 1000.0) if h_mm else None
                    height_m = h_val
                    height_source = "PROJECT_ASSUMPTION"
                    is_provisional = True
                    status = EntityStatus.REVIEW_REQUIRED
                else:
                    exceptions.append({
                        "code": "MISSING_OPENING_HEIGHT",
                        "block_name": block.name,
                        "location": (block.location.x, block.location.y),
                        "message": f"Door opening '{block.name}' at ({block.location.x:.1f}, {block.location.y:.1f}) has unknown height.",
                        "severity": "WARNING"
                    })
                    height_m = None
                    height_source = None
                    is_provisional = True
                    status = EntityStatus.REVIEW_REQUIRED
                    confidence = min(confidence, 0.70)

            # Subtype & Material Classification
            name_u = block.name.upper()
            layer_u = block.layer.upper()
            tag_u = (result.tag or "").upper()

            door_type = None
            # Project profile mapping check first
            if project_profile and project_profile.door_type_mapping:
                for k, dt in project_profile.door_type_mapping.items():
                    if k.upper() in name_u or k.upper() in tag_u:
                        door_type = dt
                        break

            if not door_type:
                if any(x in name_u for x in ("DBL", "DOUBLE", "2-LEAF", "2LEAF")) or (width_m and width_m > 1.35):
                    door_type = "double_leaf"
                elif any(x in name_u or x in layer_u for x in ("GLASS", "GLAZ", "GLZ")):
                    door_type = "glass"
                elif any(x in name_u for x in ("SLID", "SLD")):
                    door_type = "sliding"
                elif any(x in name_u for x in ("SINGLE", "SGL", "FLUSH")):
                    door_type = "single_leaf"
                else:
                    door_type = "unknown"

            material = None
            if any(x in name_u or x in layer_u for x in ("GLASS", "GLAZ", "GLZ")):
                material = "glass"
            elif any(x in name_u for x in ("WOOD", "TIMBER", "PLY")):
                material = "wood"
            elif any(x in name_u for x in ("METAL", "STEEL", "ALUM")):
                material = "metal"

            if door_type == "unknown":
                exceptions.append({
                    "code": "UNKNOWN_DOOR_SUBTYPE",
                    "block_name": block.name,
                    "location": (block.location.x, block.location.y),
                    "message": f"Door opening '{block.name}' has unknown door subtype (not single/double/glass).",
                    "severity": "WARNING"
                })
                confidence = min(confidence, 0.70)
                status = EntityStatus.REVIEW_REQUIRED

            # Topological threshold span — ZERO SILENT 900MM GAP CLOSURE
            jamb1 = None
            jamb2 = None

            if width_m is None:
                exceptions.append({
                    "code": "ROOM_BOUNDARY_REVIEW_REQUIRED",
                    "block_name": block.name,
                    "location": (block.location.x, block.location.y),
                    "message": f"Door '{block.name}' has unknown width; topological closure marked uncertain.",
                    "severity": "WARNING"
                })
                is_provisional = True
                status = EntityStatus.REVIEW_REQUIRED
                confidence = min(confidence, 0.60)
            else:
                threshold_span_mm = width_m * 1000.0
                if best_wall:
                    dx = best_wall.end.x - best_wall.start.x
                    dy = best_wall.end.y - best_wall.start.y
                    wall_angle_rad = math.atan2(dy, dx)
                    dir_rad = math.radians(block.rotation_deg) if block.rotation_deg != 0.0 else wall_angle_rad
                else:
                    dir_rad = math.radians(block.rotation_deg)

                target_p1 = block.location
                target_p2 = Point2D(
                    target_p1.x + threshold_span_mm * math.cos(dir_rad),
                    target_p1.y + threshold_span_mm * math.sin(dir_rad)
                )
                jamb1 = self._snap_to_endpoint(target_p1, wall_endpoints, max_dist_mm=250.0)
                jamb2 = self._snap_to_endpoint(target_p2, wall_endpoints, max_dist_mm=250.0)

            if best_wall and best_line:
                dx = best_wall.end.x - best_wall.start.x
                dy = best_wall.end.y - best_wall.start.y
                dir_deg = math.degrees(math.atan2(dy, dx)) if block.rotation_deg == 0.0 else block.rotation_deg

                opening = Opening(
                    id=f"OP-{door_counter:03d}",
                    opening_type=OpeningType.DOOR,
                    door_type=door_type,
                    material=material,
                    width_m=width_m,
                    height_m=height_m,
                    host_wall_id=best_wall.handle or f"WALL-{best_wall.start.to_tuple()}",
                    tag=result.tag or f"D{door_counter}",
                    location=block.location,
                    orientation_deg=dir_deg % 360.0,
                    jamb_p1=jamb1,
                    jamb_p2=jamb2,
                    detection_source="block_classifier",
                    confidence=confidence,
                    status=status,
                    is_provisional=is_provisional,
                    width_source=width_source,
                    height_source=height_source
                )
            else:
                exceptions.append({
                    "code": "LOW_CONFIDENCE_DOOR",
                    "block_name": block.name,
                    "location": (block.location.x, block.location.y),
                    "message": f"Door '{block.name}' at ({block.location.x:.1f}, {block.location.y:.1f}) has no host wall within {self.max_wall_distance_mm}mm.",
                    "severity": "WARNING"
                })

                opening = Opening(
                    id=f"OP-{door_counter:03d}",
                    opening_type=OpeningType.DOOR,
                    door_type=door_type,
                    material=material,
                    width_m=width_m,
                    height_m=height_m,
                    host_wall_id=None,
                    tag=result.tag or f"D{door_counter}",
                    location=block.location,
                    orientation_deg=block.rotation_deg,
                    jamb_p1=jamb1,
                    jamb_p2=jamb2,
                    detection_source="block_classifier",
                    confidence=min(confidence, 0.60),
                    status=EntityStatus.REVIEW_REQUIRED,
                    is_provisional=True,
                    width_source=width_source,
                    height_source=height_source
                )

            openings.append(opening)
            door_counter += 1

        return openings, non_doors, exceptions

    def _snap_to_endpoint(
        self,
        target: Point2D,
        endpoints: Sequence[Point2D],
        max_dist_mm: float = 250.0
    ) -> Point2D:
        best_pt = target
        min_dist = float("inf")
        for ep in endpoints:
            d = ep.distance_to(target)
            if d < min_dist and d <= max_dist_mm:
                min_dist = d
                best_pt = ep
        return best_pt
