"""
QS Quantification Engine — Geometric Wall Pairing & Centerline Detector
Extracts architectural wall centerlines from unlayered parallel line pairs in Vector PDFs.
Enforces Blueprint Section 15 (Module 9 — Line / Wall Detection).
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from core.geometry.primitives import Point2D, Segment2D
from core.models.semantics import WallSegment
from core.tolerances import ToleranceEvaluator

@dataclass
class WallDetectionConfig:
    min_thickness_mm: float = 75.0
    max_thickness_mm: float = 350.0
    parallel_tolerance_deg: float = 1.0
    min_overlap_mm: float = 100.0


class WallDetector:
    """Discovers paired parallel line segments and synthesizes centerline wall geometry."""

    def __init__(self, config: WallDetectionConfig | None = None):
        self.config = config or WallDetectionConfig()

    def detect_walls(self, segments: list[Segment2D]) -> list[WallSegment]:
        """Pairs parallel boundary lines and extracts centerlines with wall thickness."""
        if not segments:
            return []

        paired_indices = set()
        detected_walls: list[WallSegment] = []
        n = len(segments)

        for i in range(n):
            s1 = segments[i]
            if s1.length_mm < self.config.min_overlap_mm:
                continue

            for j in range(i + 1, n):
                if j in paired_indices:
                    continue
                s2 = segments[j]
                if s2.length_mm < self.config.min_overlap_mm:
                    continue

                # 1. Check Parallelism
                if not ToleranceEvaluator.lines_parallel(
                    s1.angle_deg,
                    s2.angle_deg,
                    self.config.parallel_tolerance_deg
                ):
                    continue

                # 2. Check Perpendicular Distance
                perp_dist = self._perpendicular_distance(s1, s2.midpoint)
                if not (self.config.min_thickness_mm <= perp_dist <= self.config.max_thickness_mm):
                    continue

                # 3. Check Longitudinal Overlap
                overlap = self._compute_overlap(s1, s2)
                if overlap and overlap[1] - overlap[0] >= self.config.min_overlap_mm:
                    paired_indices.add(i)
                    paired_indices.add(j)

                    # 4. Construct Centerline
                    centerline = self._synthesize_centerline(s1, s2, overlap)
                    detected_walls.append(WallSegment(
                        id=f"W-DET-{len(detected_walls)+1:03d}",
                        start=centerline.start,
                        end=centerline.end,
                        thickness_mm=round(perp_dist, 1),
                        confidence=0.92,
                        classification="partition" if perp_dist < 150 else "structural_wall"
                    ))
                    break

        return detected_walls

    def _perpendicular_distance(self, line_seg: Segment2D, pt: Point2D) -> float:
        """Distance from a point to the infinite line passing through line_seg."""
        p1 = line_seg.start
        p2 = line_seg.end
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        length = math.hypot(dx, dy)
        if length < 1e-6:
            return p1.distance_to(pt)
        return abs(dy * pt.x - dx * pt.y + p2.x * p1.y - p2.y * p1.x) / length

    def _compute_overlap(self, s1: Segment2D, s2: Segment2D) -> tuple[float, float] | None:
        """Projects s1 and s2 onto s1's direction vector and finds interval intersection."""
        dx = s1.end.x - s1.start.x
        dy = s1.end.y - s1.start.y
        L = math.hypot(dx, dy)
        if L < 1e-6:
            return None
        ux, uy = dx / L, dy / L

        # Projection values along s1's axis (s1 spans [0, L])
        t1_min, t1_max = 0.0, L

        # Project s2 endpoints
        t2_a = (s2.start.x - s1.start.x) * ux + (s2.start.y - s1.start.y) * uy
        t2_b = (s2.end.x - s1.start.x) * ux + (s2.end.y - s1.start.y) * uy
        t2_min, t2_max = min(t2_a, t2_b), max(t2_a, t2_b)

        start_overlap = max(t1_min, t2_min)
        end_overlap = min(t1_max, t2_max)

        if end_overlap > start_overlap:
            return (start_overlap, end_overlap)
        return None

    def _synthesize_centerline(
        self,
        s1: Segment2D,
        s2: Segment2D,
        overlap: tuple[float, float]
    ) -> Segment2D:
        """Generates the midpoint centerline segment across the overlapping interval."""
        dx = s1.end.x - s1.start.x
        dy = s1.end.y - s1.start.y
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        # Normal vector pointing from s1 towards s2
        nx, ny = -uy, ux

        # Check orientation of normal towards s2
        mid_s2 = s2.midpoint
        dot = (mid_s2.x - s1.midpoint.x) * nx + (mid_s2.y - s1.midpoint.y) * ny
        if dot < 0:
            nx, ny = -nx, -ny

        perp_dist = self._perpendicular_distance(s1, mid_s2)
        half_d = perp_dist / 2.0

        t_start, t_end = overlap
        start_pt = Point2D(
            s1.start.x + (t_start * ux) + (half_d * nx),
            s1.start.y + (t_start * uy) + (half_d * ny)
        )
        end_pt = Point2D(
            s1.start.x + (t_end * ux) + (half_d * nx),
            s1.start.y + (t_end * uy) + (half_d * ny)
        )
        return Segment2D(start=start_pt, end=end_pt, layer="CENTERLINE")

    def _point_near_segment(self, pt: Point2D, seg: Segment2D, tol_mm: float) -> bool:
        """Checks if a point is within tol_mm perpendicular distance to seg within its longitudinal span."""
        p_dist = self._perpendicular_distance(seg, pt)
        if p_dist > tol_mm:
            return False
        dx = seg.end.x - seg.start.x
        dy = seg.end.y - seg.start.y
        L = math.hypot(dx, dy)
        if L < 1e-6:
            return False
        ux, uy = dx / L, dy / L
        proj = (pt.x - seg.start.x) * ux + (pt.y - seg.start.y) * uy
        return -tol_mm <= proj <= (L + tol_mm)

    def validate_wall_candidates(
        self,
        segments: list[Segment2D],
        texts: list[any] | None = None,
        connection_tolerance_mm: float = 60.0,
        min_wall_length_mm: float = 50.0,
    ) -> list[Segment2D]:
        """
        Filters raw vector segments through WallDetector intelligence:
        1. Pre-filters out border/annotation layers (PDF_BORDER, PDF_TITLE_BLOCK, PDF_ANNOTATION)
        2. Filters out short dimension ticks (< min_wall_length_mm)
        3. Filters out dimension lines interfering directly with dimension texts
        4. Validates structural continuity and intersections (eliminates isolated floating lines like furniture/dimension lines)
        """
        if not segments:
            return []

        # 1. Pre-filter by layer and minimum length
        pre_filtered = [
            s for s in segments
            if s.layer not in ("PDF_BORDER", "PDF_TITLE_BLOCK", "PDF_ANNOTATION")
            and s.length_mm >= min_wall_length_mm
        ]

        if not pre_filtered:
            return []

        # 2. Text / Dimension interference detection
        dim_filtered: list[Segment2D] = []
        dim_texts = []
        if texts:
            import re
            num_pattern = re.compile(r"^\d+([.,]\d+)?\s*(mm|m|cm)?$", re.IGNORECASE)
            dim_texts = [t for t in texts if hasattr(t, "content") and num_pattern.match(t.content.strip())]

        for s in pre_filtered:
            is_dim_line = False
            if dim_texts:
                s_mid = s.midpoint
                for dt in dim_texts:
                    if hasattr(dt, "location") and s_mid.distance_to(dt.location) < 40.0:
                        is_dim_line = True
                        break
            if not is_dim_line:
                dim_filtered.append(s)

        if not dim_filtered:
            return []

        # 3. Continuity & Intersection analysis:
        # In architectural topology, true wall segments connect to other segments at corners / junctions.
        # An isolated segment that connects to NOTHING at either end is a floating furniture / decorative line.
        connected_segments: list[Segment2D] = []
        m = len(dim_filtered)

        for i in range(m):
            s1 = dim_filtered[i]
            has_start_conn = False
            has_end_conn = False

            for j in range(m):
                if i == j:
                    continue
                s2 = dim_filtered[j]

                if not has_start_conn:
                    if (s1.start.distance_to(s2.start) <= connection_tolerance_mm or
                        s1.start.distance_to(s2.end) <= connection_tolerance_mm or
                        self._point_near_segment(s1.start, s2, connection_tolerance_mm)):
                        has_start_conn = True

                if not has_end_conn:
                    if (s1.end.distance_to(s2.end) <= connection_tolerance_mm or
                        s1.end.distance_to(s2.start) <= connection_tolerance_mm or
                        self._point_near_segment(s1.end, s2, connection_tolerance_mm)):
                        has_end_conn = True

                if has_start_conn and has_end_conn:
                    break

            # If segment connects at least at one end (e.g. wall corner, stub or T-junction), keep it
            if has_start_conn or has_end_conn:
                connected_segments.append(s1)

        return connected_segments
