"""
QS Quantification Engine — Geometric Tolerances & Snapping Profiles
Enforces micro-level precision rules based on Blueprint Section 73.
"""

import math
from dataclasses import dataclass

@dataclass(frozen=True)
class ToleranceProfile:
    """Configurable tolerance profile for CAD geometry reconciliation."""
    name: str = "Standard Interior CAD"
    endpoint_snap_mm: float = 3.0
    parallel_angle_deg: float = 1.0
    room_gap_close_max_mm: float = 20.0
    duplicate_distance_mm: float = 2.0
    min_room_area_sqm: float = 2.5
    sliver_ratio_threshold: float = 25.0  # perimeter^2 / area ratio for slivers

DEFAULT_TOLERANCES = ToleranceProfile()


class ToleranceEvaluator:
    """Helper methods for tolerance checks and spatial snapping."""

    @staticmethod
    def points_coincide(p1: tuple[float, float], p2: tuple[float, float], tolerance_mm: float = 3.0) -> bool:
        """Returns True if two points are within the snap tolerance."""
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        return (dx * dx + dy * dy) <= (tolerance_mm * tolerance_mm)

    @staticmethod
    def distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
        """Euclidean distance between two 2D points in mm."""
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        return math.hypot(dx, dy)

    @staticmethod
    def lines_parallel(angle1_deg: float, angle2_deg: float, tolerance_deg: float = 1.0) -> bool:
        """Checks if two angles are parallel within angular tolerance (accounts for 180° flip)."""
        diff = abs((angle1_deg - angle2_deg) % 180.0)
        return diff <= tolerance_deg or (180.0 - diff) <= tolerance_deg
