"""
QS Quantification Engine — Geometric Symbol Detection Engine
Identifies standard architectural symbols (doors, swings) using geometric signatures.
Enforces Blueprint Section 18 (Module 12 — Symbol Detection).
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from core.geometry.primitives import Point2D, Segment2D, Arc2D
from core.tolerances import ToleranceEvaluator

@dataclass(frozen=True)
class DetectedDoorSymbol:
    hinge: Point2D
    width_mm: float
    sweep_angle_deg: float
    confidence: float
    source_arc_handle: str

    @property
    def width_m(self) -> float:
        return self.width_mm / 1000.0


class GeometricSymbolDetector:
    """Detects doors and openings by pairing door leaf line segments with swing arcs."""

    def __init__(
        self,
        min_door_width_mm: float = 650.0,
        max_door_width_mm: float = 1300.0,
        arc_sweep_tolerance_deg: float = 15.0
    ):
        self.min_door_width_mm = min_door_width_mm
        self.max_door_width_mm = max_door_width_mm
        self.arc_sweep_tolerance_deg = arc_sweep_tolerance_deg

    def detect_doors_from_geometry(
        self,
        segments: list[Segment2D],
        arcs: list[Arc2D]
    ) -> list[DetectedDoorSymbol]:
        """Discovers door swings by pairing ~90° arcs with radial leaf segments."""
        detected_doors: list[DetectedDoorSymbol] = []

        for arc in arcs:
            # Check if arc radius fits door width range
            if not (self.min_door_width_mm <= arc.radius <= self.max_door_width_mm):
                continue

            # Check if arc sweep angle is approximately 90 degrees (quarter circle)
            sweep = arc.sweep_angle_deg
            if abs(sweep - 90.0) > self.arc_sweep_tolerance_deg:
                continue

            # Look for a matching leaf line segment starting near arc center (the hinge)
            hinge = arc.center
            leaf_found = False

            for seg in segments:
                # Segment length should match arc radius within 15%
                if abs(seg.length_mm - arc.radius) / arc.radius > 0.15:
                    continue

                # One endpoint must be near the hinge
                if ToleranceEvaluator.points_coincide(seg.start.to_tuple(), hinge.to_tuple(), tolerance_mm=30.0) or \
                   ToleranceEvaluator.points_coincide(seg.end.to_tuple(), hinge.to_tuple(), tolerance_mm=30.0):
                    leaf_found = True
                    break

            confidence = 0.96 if leaf_found else 0.88
            detected_doors.append(DetectedDoorSymbol(
                hinge=hinge,
                width_mm=round(arc.radius, 1),
                sweep_angle_deg=round(sweep, 1),
                confidence=confidence,
                source_arc_handle=arc.handle
            ))

        return detected_doors
