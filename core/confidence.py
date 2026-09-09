"""
QS Quantification Engine — Confidence Fusion Engine
Fuses multi-modal signals (layers, blocks, geometry, OCR, detector) into calibrated scores.
Enforces Blueprint Section 33, 34, & 105 (Confidence Fusion).
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass

class ReviewStatus(str, Enum):
    AUTO_ACCEPT = "auto_accept"          # >= 0.95
    VISIBLE_REVIEW = "visible_review"    # 0.80 - 0.95
    MANDATORY_REVIEW = "mandatory_review" # 0.60 - 0.80
    EXCEPTION = "exception"              # < 0.60


@dataclass
class SignalWeights:
    """Configurable weights per signal modality."""
    w_layer: float = 0.25
    w_block: float = 0.30
    w_geometry: float = 0.25
    w_ocr: float = 0.15
    w_detector: float = 0.05


class ConfidenceEngine:
    """Fuses multi-modal signals into an overall confidence score and review status."""

    @staticmethod
    def fuse_signals(
        layer_signal: float | None = None,
        block_signal: float | None = None,
        geometry_signal: float | None = None,
        ocr_signal: float | None = None,
        detector_signal: float | None = None,
        weights: SignalWeights | None = None
    ) -> float:
        """Computes weighted average across active signals."""
        w = weights or SignalWeights()
        active_pairs = []

        if layer_signal is not None:
            active_pairs.append((w.w_layer, layer_signal))
        if block_signal is not None:
            active_pairs.append((w.w_block, block_signal))
        if geometry_signal is not None:
            active_pairs.append((w.w_geometry, geometry_signal))
        if ocr_signal is not None:
            active_pairs.append((w.w_ocr, ocr_signal))
        if detector_signal is not None:
            active_pairs.append((w.w_detector, detector_signal))

        if not active_pairs:
            return 0.50

        total_weight = sum(weight for weight, _ in active_pairs)
        fused = sum(weight * val for weight, val in active_pairs) / total_weight
        return round(fused, 3)

    @staticmethod
    def evaluate_status(confidence: float) -> ReviewStatus:
        """Classifies a confidence score into its review tier."""
        if confidence >= 0.95:
            return ReviewStatus.AUTO_ACCEPT
        elif confidence >= 0.80:
            return ReviewStatus.VISIBLE_REVIEW
        elif confidence >= 0.60:
            return ReviewStatus.MANDATORY_REVIEW
        else:
            return ReviewStatus.EXCEPTION
