"""
QS Quantification Engine — IS 1200 / POMI Advanced Trade Measurement Rules
Enforces statutory construction deduction thresholds:
- IS 1200 Part 7 (Plastering & Ceiling): Clause 4.1.1 (0.40 sqm opening deduction threshold).
- IS 1200 Part 11 (Paving & Flooring): Clause 3.4 (0.20 sqm cutout threshold + door rebate threshold extension).
- IS 1200 Part 4 (Partitions & Walls): Opening deductions & centerline intersections.
"""

from __future__ import annotations
from dataclasses import dataclass
from core.geometry.primitives import Polygon2D, Point2D
from core.models.semantics import Opening

# Statutory deduction thresholds
IS1200_CEILING_DEDUCTION_THRESHOLD_SQM = 0.40  # Openings <= 0.40 sqm are NOT deductible
IS1200_FLOORING_DEDUCTION_THRESHOLD_SQM = 0.20  # Floor cutouts <= 0.20 sqm are NOT deductible

@dataclass
class IS1200CeilingTakeoffResult:
    gross_area_sqm: float
    deducted_openings_sqm: float
    ignored_openings_sqm: float
    net_ceiling_area_sqm: float
    formula_lineage: str


@dataclass
class IS1200FlooringTakeoffResult:
    room_polygon_area_sqm: float
    deducted_voids_sqm: float
    door_rebates_added_sqm: float
    net_flooring_area_sqm: float
    formula_lineage: str


class IS1200TradeRules:
    """Implements statutory IS 1200 & POMI construction measurement deduction rules."""

    @staticmethod
    def calculate_ceiling_with_thresholds(
        room_poly: Polygon2D,
        ceiling_cutouts: list[Polygon2D] | None = None
    ) -> IS1200CeilingTakeoffResult:
        """
        Calculates ceiling area per IS 1200 Part 7:
        - Openings <= 0.40 sqm (2x2 lights, AC diffusers, small trap doors) are NOT deducted.
        - Openings > 0.40 sqm (duct shafts, large voids) are deducted.
        """
        gross_area_sqm = room_poly.gross_area_mm2 * 1e-6
        cutouts = ceiling_cutouts or []

        deducted_sqm = 0.0
        ignored_sqm = 0.0
        deducted_count = 0
        ignored_count = 0

        for c in cutouts:
            c_area_sqm = c.gross_area_mm2 * 1e-6
            if c_area_sqm > IS1200_CEILING_DEDUCTION_THRESHOLD_SQM:
                deducted_sqm += c_area_sqm
                deducted_count += 1
            else:
                ignored_sqm += c_area_sqm
                ignored_count += 1

        net_area_sqm = max(0.0, gross_area_sqm - deducted_sqm)

        formula = (
            f"Gross Ceiling ({gross_area_sqm:.3f} sqm) - "
            f"Deductible Openings >0.4sqm ({deducted_sqm:.3f} sqm from {deducted_count} voids) = "
            f"{net_area_sqm:.3f} sqm [IS 1200 Part 7: {ignored_count} openings <=0.4sqm not deducted]"
        )

        return IS1200CeilingTakeoffResult(
            gross_area_sqm=gross_area_sqm,
            deducted_openings_sqm=deducted_sqm,
            ignored_openings_sqm=ignored_sqm,
            net_ceiling_area_sqm=net_area_sqm,
            formula_lineage=formula
        )

    @staticmethod
    def calculate_flooring_with_door_rebates(
        room_poly: Polygon2D,
        floor_cutouts: list[Polygon2D] | None = None,
        doors: list[Opening] | None = None,
        door_jamb_depth_mm: float = 75.0
    ) -> IS1200FlooringTakeoffResult:
        """
        Calculates flooring area per IS 1200 Part 11:
        - Floor voids <= 0.20 sqm are NOT deducted.
        - Floor voids > 0.20 sqm are deducted.
        - Flooring extends into door openings up to the frame rebate (width * jamb_depth).
        """
        base_area_sqm = room_poly.gross_area_mm2 * 1e-6
        cutouts = floor_cutouts or []
        doors = doors or []

        deducted_voids_sqm = 0.0
        for c in cutouts:
            c_area_sqm = c.gross_area_mm2 * 1e-6
            if c_area_sqm > IS1200_FLOORING_DEDUCTION_THRESHOLD_SQM:
                deducted_voids_sqm += c_area_sqm

        # Add door threshold rebate area (width in m * jamb depth in m)
        door_rebates_sqm = 0.0
        for d in doors:
            door_rebates_sqm += d.width_m * (door_jamb_depth_mm / 1000.0)

        net_area_sqm = max(0.0, base_area_sqm - deducted_voids_sqm + door_rebates_sqm)

        formula = (
            f"Room Area ({base_area_sqm:.3f} sqm) - "
            f"Voids >0.2sqm ({deducted_voids_sqm:.3f} sqm) + "
            f"Door Rebates ({door_rebates_sqm:.3f} sqm from {len(doors)} doors) = "
            f"{net_area_sqm:.3f} sqm"
        )

        return IS1200FlooringTakeoffResult(
            room_polygon_area_sqm=base_area_sqm,
            deducted_voids_sqm=deducted_voids_sqm,
            door_rebates_added_sqm=door_rebates_sqm,
            net_flooring_area_sqm=net_area_sqm,
            formula_lineage=formula
        )

    @staticmethod
    def calculate_skirting_with_columns(
        room_poly: Polygon2D,
        doors: list[Opening] | None = None
    ) -> tuple[float, str]:
        """
        Perimeter skirting per IS 1200:
        Measures total internal perimeter (including column faces protruding into room)
        minus clear door openings.
        """
        gross_perimeter_m = room_poly.perimeter_mm * 1e-3
        doors = doors or []
        total_door_width_m = sum(d.width_m for d in doors)
        net_skirting_m = max(0.0, gross_perimeter_m - total_door_width_m)

        formula = (
            f"Gross Internal Perimeter ({gross_perimeter_m:.3f}m) - "
            f"Clear Door Openings ({total_door_width_m:.3f}m) = "
            f"{net_skirting_m:.3f} m"
        )
        return net_skirting_m, formula
