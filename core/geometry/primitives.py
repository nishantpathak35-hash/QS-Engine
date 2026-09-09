"""
QS Quantification Engine — Core 2D Geometric Primitives
Micro-detailed mathematical implementations: Shoelace formula, segment metrics, centroids.
Zero external GIS or web dependencies — pure Python algorithms.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from core.tolerances import ToleranceEvaluator

@dataclass(frozen=True)
class Point2D:
    x: float
    y: float

    def to_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)

    def distance_to(self, other: Point2D) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def is_coincident_with(self, other: Point2D, tolerance_mm: float = 3.0) -> bool:
        return self.distance_to(other) <= tolerance_mm


@dataclass(frozen=True)
class Segment2D:
    start: Point2D
    end: Point2D
    layer: str = "0"
    handle: str = ""

    @property
    def length_mm(self) -> float:
        return self.start.distance_to(self.end)

    @property
    def angle_deg(self) -> float:
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        return math.degrees(math.atan2(dy, dx)) % 360.0

    @property
    def midpoint(self) -> Point2D:
        return Point2D(
            (self.start.x + self.end.x) / 2.0,
            (self.start.y + self.end.y) / 2.0
        )

    def is_parallel_to(self, other: Segment2D, tolerance_deg: float = 1.0) -> bool:
        return ToleranceEvaluator.lines_parallel(self.angle_deg, other.angle_deg, tolerance_deg)


@dataclass(frozen=True)
class Arc2D:
    center: Point2D
    radius: float
    start_angle_deg: float
    end_angle_deg: float
    layer: str = "0"
    handle: str = ""

    @property
    def sweep_angle_deg(self) -> float:
        sweep = (self.end_angle_deg - self.start_angle_deg) % 360.0
        return sweep if sweep > 0 else 360.0

    @property
    def radius_mm(self) -> float:
        return self.radius

    @property
    def arc_length_mm(self) -> float:
        return (math.radians(self.sweep_angle_deg) * self.radius)


@dataclass
class Polygon2D:
    """Represents a closed 2D polygon with optional interior holes."""
    vertices: list[Point2D]
    holes: list[list[Point2D]] = field(default_factory=list)

    def __post_init__(self):
        if len(self.vertices) < 3:
            raise ValueError("Polygon must contain at least 3 vertices.")
        # Ensure vertices are not duplicated at start/end for shoelace
        if self.vertices[0].is_coincident_with(self.vertices[-1], tolerance_mm=0.001):
            self.vertices.pop()

    @staticmethod
    def _shoelace_area(points: list[Point2D]) -> float:
        """Calculates area using the Shoelace formula (Green's Theorem)."""
        n = len(points)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += points[i].x * points[j].y
            area -= points[j].x * points[i].y
        return abs(area) / 2.0

    @property
    def gross_area_mm2(self) -> float:
        """Gross area of the outer boundary in mm²."""
        return self._shoelace_area(self.vertices)

    @property
    def holes_area_mm2(self) -> float:
        """Summed area of all interior holes (cutouts/openings) in mm²."""
        return sum(self._shoelace_area(h) for h in self.holes)

    @property
    def net_area_mm2(self) -> float:
        """Net measurable area (Gross - Holes) in mm²."""
        return max(0.0, self.gross_area_mm2 - self.holes_area_mm2)

    @property
    def perimeter_mm(self) -> float:
        """Perimeter of outer boundary in mm."""
        n = len(self.vertices)
        perim = 0.0
        for i in range(n):
            j = (i + 1) % n
            perim += self.vertices[i].distance_to(self.vertices[j])
        return perim

    @property
    def centroid(self) -> Point2D:
        """Calculates the geometric centroid of the outer boundary."""
        n = len(self.vertices)
        cx, cy = 0.0, 0.0
        signed_area = 0.0
        for i in range(n):
            j = (i + 1) % n
            factor = (self.vertices[i].x * self.vertices[j].y) - (self.vertices[j].x * self.vertices[i].y)
            cx += (self.vertices[i].x + self.vertices[j].x) * factor
            cy += (self.vertices[i].y + self.vertices[j].y) * factor
            signed_area += factor
        signed_area *= 0.5
        if abs(signed_area) < 1e-9:
            return self.vertices[0]
        cx /= (6.0 * signed_area)
        cy /= (6.0 * signed_area)
        return Point2D(cx, cy)

    def contains_point(self, pt: Point2D) -> bool:
        """Ray-casting algorithm for Point-in-Polygon testing."""
        inside = False
        n = len(self.vertices)
        for i in range(n):
            j = (i + 1) % n
            xi, yi = self.vertices[i].x, self.vertices[i].y
            xj, yj = self.vertices[j].x, self.vertices[j].y
            intersect = ((yi > pt.y) != (yj > pt.y)) and (pt.x < (xj - xi) * (pt.y - yi) / (yj - yi + 1e-12) + xi)
            if intersect:
                inside = not inside
        return inside
