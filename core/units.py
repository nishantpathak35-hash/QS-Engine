"""
QS Quantification Engine — Canonical Unit Normalization System
All internal geometry calculations MUST strictly use Millimeters (mm).
Preserves raw mathematical precision while offering standardized QS display units.
"""

from enum import Enum
from dataclasses import dataclass

class UnitCategory(str, Enum):
    LENGTH = "length"
    AREA = "area"
    VOLUME = "volume"
    COUNT = "count"


class DisplayUnit(str, Enum):
    MM = "mm"
    M = "m"
    SQM = "sqm"
    SQFT = "sqft"
    RFT = "rft"
    CUM = "cum"
    NOS = "nos"


# Exact conversion factors
MM_TO_M = 0.001
MM2_TO_SQM = 1e-6
SQM_TO_SQFT = 10.763910416709722
M_TO_RFT = 3.280839895013123
MM3_TO_CUM = 1e-9


@dataclass(frozen=True)
class FormattedQuantity:
    """Represents a calculated quantity preserving raw precision alongside display values."""
    raw_value: float
    display_value: float
    unit: DisplayUnit
    category: UnitCategory

    def __str__(self) -> str:
        if self.unit == DisplayUnit.NOS:
            return f"{int(self.display_value)} {self.unit.value}"
        return f"{self.display_value:.2f} {self.unit.value}"


class UnitsEngine:
    """Deterministic conversion utility for QS quantities."""

    @staticmethod
    def mm_to_m(val_mm: float) -> float:
        return val_mm * MM_TO_M

    @staticmethod
    def mm2_to_sqm(val_mm2: float) -> float:
        return val_mm2 * MM2_TO_SQM

    @staticmethod
    def sqm_to_sqft(val_sqm: float) -> float:
        return val_sqm * SQM_TO_SQFT

    @staticmethod
    def m_to_rft(val_m: float) -> float:
        return val_m * M_TO_RFT

    @staticmethod
    def format_area_sqm(area_mm2: float, decimals: int = 2) -> FormattedQuantity:
        sqm = UnitsEngine.mm2_to_sqm(area_mm2)
        return FormattedQuantity(
            raw_value=sqm,
            display_value=round(sqm, decimals),
            unit=DisplayUnit.SQM,
            category=UnitCategory.AREA
        )

    @staticmethod
    def format_length_m(length_mm: float, decimals: int = 2) -> FormattedQuantity:
        m = UnitsEngine.mm_to_m(length_mm)
        return FormattedQuantity(
            raw_value=m,
            display_value=round(m, decimals),
            unit=DisplayUnit.M,
            category=UnitCategory.LENGTH
        )

    @staticmethod
    def format_count(count: int) -> FormattedQuantity:
        return FormattedQuantity(
            raw_value=float(count),
            display_value=float(count),
            unit=DisplayUnit.NOS,
            category=UnitCategory.COUNT
        )
