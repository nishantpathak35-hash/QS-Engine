"""
QS Quantification Engine — Vector PDF Scale Calibration Engine
Converts dimensionless PDF points (72 pt/inch) to true physical millimeters.
Enforces Blueprint Section 10 (Module 4 — Scale Engine).
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from core.exceptions import ScaleRequiredError

# 1 PDF typographic point = 25.4 / 72 mm on physical paper sheet
PT_TO_PAPER_MM = 25.4 / 72.0


@dataclass(frozen=True)
class CalibratedScale:
    scale_factor_mm_per_pt: float
    source: str
    ratio_string: str
    confidence: float

    @property
    def scale_ratio(self) -> int:
        if ":" in self.ratio_string:
            try:
                return int(self.ratio_string.split(":")[-1])
            except ValueError:
                pass
        return 1


class ScaleCalibrator:
    """Calculates the physical millimeter scale factor for vector PDF drawings."""

    # Regex patterns for architectural scale notes
    SCALE_REGEXES = [
        re.compile(r"scale\s*[:\-=]?\s*1\s*:\s*(\d+)", re.IGNORECASE),
        re.compile(r"1\s*:\s*(\d+)\s*scale", re.IGNORECASE),
        re.compile(r"\b1\s*:\s*(\d+)\b"),
    ]

    @classmethod
    def calibrate_from_text(cls, text_corpus: str) -> CalibratedScale | None:
        """Attempts to discover standard architectural scale notes (e.g. 1:100, 1:50)."""
        for pattern in cls.SCALE_REGEXES:
            match = pattern.search(text_corpus)
            if match:
                ratio = int(match.group(1))
                # Reasonable architectural scale check (1:5 to 1:1000)
                if 5 <= ratio <= 1000:
                    scale_mm_per_pt = PT_TO_PAPER_MM * float(ratio)
                    return CalibratedScale(
                        scale_factor_mm_per_pt=scale_mm_per_pt,
                        source="explicit_scale_note",
                        ratio_string=f"1:{ratio}",
                        confidence=0.98
                    )
        return None

    @classmethod
    def calibrate_from_dimension(cls, dimension_val_mm: float, segment_length_pt: float) -> CalibratedScale:
        """Calibrates scale from a known dimension line (e.g. 3000mm on a 85pt vector line)."""
        if segment_length_pt <= 0:
            raise ValueError("Segment length in points must be positive.")
        scale_mm_per_pt = dimension_val_mm / segment_length_pt
        ratio = round(scale_mm_per_pt / PT_TO_PAPER_MM)
        return CalibratedScale(
            scale_factor_mm_per_pt=scale_mm_per_pt,
            source="dimension_measurement",
            ratio_string=f"1:{ratio}",
            confidence=0.95
        )

    @classmethod
    def calibrate_or_fail(
        cls,
        text_corpus: str,
        user_scale_ratio: int | None = None
    ) -> CalibratedScale:
        """Strict resolution: returns calibrated scale or raises ScaleRequiredError."""
        if user_scale_ratio is not None and user_scale_ratio > 0:
            return CalibratedScale(
                scale_factor_mm_per_pt=PT_TO_PAPER_MM * float(user_scale_ratio),
                source="user_calibration",
                ratio_string=f"1:{user_scale_ratio}",
                confidence=1.0
            )

        calibrated = cls.calibrate_from_text(text_corpus)
        if calibrated:
            return calibrated

        raise ScaleRequiredError(
            "Scale could not be established from drawing text notes. "
            "Please provide scale ratio (e.g. 1:100) or calibrate using a known dimension."
        )
