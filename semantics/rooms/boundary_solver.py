"""
QS Quantification Engine — Topological Planar Face & Room Boundary Solver
Converts wall segments into closed spatial regions using computational geometry.
Enforces Blueprint Section 16 (Module 10) & Section 73 (Geometry Tolerances).
"""

from __future__ import annotations
from typing import Sequence
import shapely.geometry as sg
import shapely.ops as so

from core.geometry.primitives import Point2D, Polygon2D, Segment2D
from core.models.semantics import Room, Opening, EntityStatus
from core.tolerances import ToleranceProfile, DEFAULT_TOLERANCES
from parsers.dxf.reader import ExtractedText
from vision.ocr.text_classifier import TextContextClassifier, TextCategory

class RoomBoundarySolver:
    """Detects closed interior room regions from wall segments and text annotations."""

    def __init__(self, tolerances: ToleranceProfile = DEFAULT_TOLERANCES):
        self.tolerances = tolerances
        self.exceptions: list[dict] = []

    def solve_rooms(
        self,
        wall_segments: Sequence[Segment2D],
        annotations: Sequence[ExtractedText],
        door_openings: Sequence[Opening] | None = None
    ) -> list[Room]:
        """Reconstructs closed room polygons from wall segments and matches labels."""
        if not wall_segments:
            return []

        # Convert Segment2D to Shapely LineString
        lines = [
            sg.LineString([seg.start.to_tuple(), seg.end.to_tuple()])
            for seg in wall_segments
            if seg.length_mm > self.tolerances.duplicate_distance_mm
        ]

        if not lines:
            return []

        # 1. Orientation-aware door threshold gap bridging
        closure_lines = []
        provisional_doors = []
        if door_openings:
            for door in door_openings:
                thresh = door.get_threshold_segment()
                if thresh is not None:
                    p1, p2 = thresh
                    closure_lines.append(sg.LineString([p1.to_tuple(), p2.to_tuple()]))
                elif door.is_provisional or door.width_m is None:
                    provisional_doors.append(door)

        all_input_lines = lines + closure_lines
        multi_lines = sg.MultiLineString(all_input_lines)

        # Snap endpoints within tolerance
        snapped_lines = so.snap(
            multi_lines,
            multi_lines,
            self.tolerances.endpoint_snap_mm
        )

        # 2. Node the lines (split lines at all intersections)
        noded = so.unary_union(snapped_lines)

        # 3. Polygonize into closed planar faces
        raw_faces = list(so.polygonize(noded))
        if not raw_faces:
            return []

        # 4. Topological Face Filtering (Single-Room and Multi-Room Reliability)
        # Filter 4a: Discard tiny slivers below minimum room area threshold
        valid_candidates: list[sg.Polygon] = []
        for poly in raw_faces:
            area_sqm = poly.area * 1e-6
            if area_sqm < self.tolerances.min_room_area_sqm:
                continue

            # Filter 4b: Discard wall cavities (e.g. narrow double-wall gap)
            # Hydraulic radius / average thickness approx = 2 * Area / Perimeter
            perim_mm = poly.length
            if perim_mm > 0:
                avg_thickness_mm = 2.0 * poly.area / perim_mm
                if avg_thickness_mm <= 350.0 and area_sqm < 15.0:
                    # Wall cavity, not a usable room
                    continue

            valid_candidates.append(poly)

        if not valid_candidates:
            return []

        # Filter 4c: Identify and discard enclosing exterior boundaries
        # If there are multiple candidate polygons and one polygon strictly contains other
        # valid room polygons, that polygon is an outer boundary shell enclosing rooms.
        # NEVER discard a single valid room.
        filtered_faces: list[sg.Polygon] = []
        if len(valid_candidates) == 1:
            filtered_faces = valid_candidates
        else:
            for poly in valid_candidates:
                # Check if this polygon contains the centroid of ANY other candidate polygon
                contains_other = False
                for other in valid_candidates:
                    if poly != other and poly.contains(other.centroid):
                        contains_other = True
                        break
                if not contains_other:
                    filtered_faces.append(poly)

        rooms: list[Room] = []
        room_counter = 1

        for poly in filtered_faces:
            # Convert outer boundary vertices to Point2D
            ext_coords = list(poly.exterior.coords)
            vertices = [Point2D(x, y) for x, y in ext_coords[:-1]]

            # Convert interior holes (structural columns, shafts)
            holes = []
            for interior in poly.interiors:
                h_coords = list(interior.coords)
                holes.append([Point2D(x, y) for x, y in h_coords[:-1]])

            polygon_2d = Polygon2D(vertices=vertices, holes=holes)

            # Match room text annotations using TextContextClassifier
            candidate_room_names: list[tuple[str, Point2D]] = []
            matched_finish_code: str | None = None
            matched_skirting_code: str | None = None
            matched_ceiling_code: str | None = None

            for anno in annotations:
                pt = anno.location
                if polygon_2d.contains_point(pt):
                    cat, val = TextContextClassifier.classify_text(anno.content)
                    if cat == TextCategory.ROOM_NAME:
                        candidate_room_names.append((str(val or anno.content).strip(), pt))
                    elif cat == TextCategory.FINISH_CODE:
                        code_str = str(val or anno.content).strip().upper()
                        if code_str.startswith("SK"):
                            matched_skirting_code = code_str
                        elif code_str.startswith("CL") or code_str.startswith("C-"):
                            matched_ceiling_code = code_str
                        else:
                            matched_finish_code = code_str

            area_sqm = polygon_2d.net_area_mm2 * 1e-6
            base_score = 0.85

            if len(candidate_room_names) == 1:
                matched_name, matched_label_pt = candidate_room_names[0]
                base_score += 0.12
                status = EntityStatus.AUTO_MEASURED
            elif len(candidate_room_names) > 1:
                matched_name, matched_label_pt = candidate_room_names[0]
                base_score -= 0.20
                status = EntityStatus.REVIEW_REQUIRED
                labels_str = [n for n, _ in candidate_room_names]
                self.exceptions.append({
                    "code": "AMBIGUOUS_ROOM_LABEL",
                    "room_id": f"R-{room_counter:03d}",
                    "message": f"Room contains multiple conflicting room labels: {labels_str}",
                    "severity": "WARNING"
                })
            else:
                # If there are multiple candidate faces and this unlabeled polygon is small (< 3.5 sqm),
                # it represents an office workstation cubicle, desk, or fixture box, NOT an architectural room.
                if len(filtered_faces) > 1 and area_sqm < 3.5:
                    continue
                matched_name = f"Room_{room_counter:02d} (Unlabeled)"
                matched_label_pt = None
                base_score -= 0.15
                status = EntityStatus.REVIEW_REQUIRED

            # Wall-supported boundary ratio check (Requirement 9)
            ext_line = poly.exterior
            supported_len = 0.0
            for l in lines:
                if ext_line.distance(l) <= 150.0:
                    supported_len += min(l.length, ext_line.length)
            wall_support_ratio = min(1.0, supported_len / max(1.0, ext_line.length))
            if wall_support_ratio < 0.70:
                base_score -= 0.15
                status = EntityStatus.REVIEW_REQUIRED

            # Minimum sensible room area check — reject/review furniture contamination
            if area_sqm < 2.50:
                base_score -= 0.25
                status = EntityStatus.REVIEW_REQUIRED
                self.exceptions.append({
                    "code": "LOW_CONFIDENCE_ROOM_POLYGON",
                    "room_id": f"R-{room_counter:03d}",
                    "location": matched_name,
                    "message": f"Polygon '{matched_name}' has area {area_sqm:.2f} sqm (<2.5 sqm). Suspected furniture loop or fixture region.",
                    "severity": "WARNING"
                })

            # Check if any provisional/uncertain opening touches this room boundary
            has_uncertain_boundary = False
            for p_door in provisional_doors:
                d_pt = sg.Point(p_door.location.x, p_door.location.y)
                if poly.exterior.distance(d_pt) <= 350.0:
                    has_uncertain_boundary = True
                    status = EntityStatus.REVIEW_REQUIRED
                    base_score -= 0.15
                    self.exceptions.append({
                        "code": "ROOM_BOUNDARY_REVIEW_REQUIRED",
                        "room_id": f"R-{room_counter:03d}",
                        "location": matched_name,
                        "message": f"Room '{matched_name}' boundary intersects unverified opening '{p_door.tag or p_door.id}'. Status marked REVIEW_REQUIRED.",
                        "severity": "WARNING"
                    })
                    break

            final_confidence = round(max(0.30, min(0.99, base_score)), 2)
            if final_confidence < 0.80:
                status = EntityStatus.REVIEW_REQUIRED

            room = Room(
                id=f"R-{room_counter:03d}",
                name=matched_name,
                polygon=polygon_2d,
                label_point=matched_label_pt,
                finish_code=matched_finish_code,
                skirting_finish_code=matched_skirting_code,
                ceiling_finish_code=matched_ceiling_code,
                confidence=final_confidence,
                status=status,
                has_uncertain_boundary=has_uncertain_boundary,
                boundary_source="wall_detector"
            )
            rooms.append(room)
            room_counter += 1

        return rooms
