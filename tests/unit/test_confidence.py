"""
Unit Tests for Confidence Fusion & Exception Registry
"""

import pytest
from core.confidence import ConfidenceEngine, ReviewStatus
from core.exception_registry import ExceptionRegistry, ExceptionCode

def test_confidence_fusion_auto_accept():
    # Strong CAD layer + known block + geometry match
    score = ConfidenceEngine.fuse_signals(
        layer_signal=0.99,
        block_signal=0.99,
        geometry_signal=0.95
    )
    assert score >= 0.95
    assert ConfidenceEngine.evaluate_status(score) == ReviewStatus.AUTO_ACCEPT

def test_confidence_fusion_low_signals():
    # Only noisy OCR and weak detector
    score = ConfidenceEngine.fuse_signals(
        ocr_signal=0.65,
        detector_signal=0.55
    )
    assert score < 0.70
    assert ConfidenceEngine.evaluate_status(score) in (ReviewStatus.MANDATORY_REVIEW, ReviewStatus.EXCEPTION)

def test_exception_registry_lifecycle():
    registry = ExceptionRegistry()
    exc = registry.record_exception(
        code=ExceptionCode.SCALE_REQUIRED,
        drawing_id="DRW-009",
        message="Scale text not found",
        suggested_action="Enter scale ratio"
    )

    assert registry.has_blocking_exceptions is True
    assert len(registry.get_pending_exceptions()) == 1

    # Resolve exception
    exc.resolve(value="1:100", user_id="lead_qs")
    assert exc.resolved is True
    assert exc.resolution_value == "1:100"
    assert registry.has_blocking_exceptions is False
