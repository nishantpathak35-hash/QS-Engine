"""
QS Quantification Engine — Exception Registry & Human-in-the-Loop Tracker
Tracks exceptions encountered during ingestion and calculation.
Enforces Blueprint Section 35 (Exception Engine).
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

class ExceptionCode(str, Enum):
    SCALE_REQUIRED = "SCALE_REQUIRED"
    SCALE_NOT_FOUND = "SCALE_NOT_FOUND"
    UNIT_REQUIRED = "UNIT_REQUIRED"
    UNSUPPORTED_UNIT = "UNSUPPORTED_UNIT"
    ROOM_BOUNDARY_OPEN = "ROOM_BOUNDARY_OPEN"
    UNKNOWN_SYMBOL = "UNKNOWN_SYMBOL"
    UNKNOWN_BLOCK = "UNKNOWN_BLOCK"
    MISSING_HEIGHT = "MISSING_HEIGHT"
    MISSING_WALL_HEIGHT = "MISSING_WALL_HEIGHT"
    MISSING_OPENING_WIDTH = "MISSING_OPENING_WIDTH"
    MISSING_OPENING_HEIGHT = "MISSING_OPENING_HEIGHT"
    UNKNOWN_FLOOR_FINISH = "UNKNOWN_FLOOR_FINISH"
    UNKNOWN_CEILING_FINISH = "UNKNOWN_CEILING_FINISH"
    LOW_CONFIDENCE_DOOR = "LOW_CONFIDENCE_DOOR"
    LOW_OCR_CONFIDENCE = "LOW_OCR_CONFIDENCE"
    AMBIGUOUS_LABEL = "AMBIGUOUS_LABEL"
    AMBIGUOUS_ROOM_LABEL = "AMBIGUOUS_ROOM_LABEL"
    UNSUPPORTED_DRAWING = "UNSUPPORTED_DRAWING"
    RASTER_PROCESSING_NOT_SUPPORTED = "RASTER_PROCESSING_NOT_SUPPORTED"


class ExceptionSeverity(str, Enum):
    BLOCKING = "BLOCKING"      # Stops quantity calculation completely
    WARNING = "WARNING"        # Flags quantity as REVIEW_REQUIRED
    INFO = "INFO"              # Audit note / default applied


@dataclass
class ExceptionRecord:
    id: str
    code: ExceptionCode
    drawing_id: str
    message: str
    severity: ExceptionSeverity = ExceptionSeverity.WARNING
    entity_id: str | None = None
    suggested_action: str = ""
    suggested_default: float | str | None = None
    resolved: bool = False
    resolution_value: float | str | None = None
    resolved_by: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def resolve(self, value: float | str, user_id: str = "estimator"):
        self.resolved = True
        self.resolution_value = value
        self.resolved_by = user_id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code.value,
            "drawing_id": self.drawing_id,
            "message": self.message,
            "severity": self.severity.value,
            "entity_id": self.entity_id,
            "suggested_action": self.suggested_action,
            "suggested_default": self.suggested_default,
            "resolved": self.resolved,
            "resolution_value": self.resolution_value,
            "resolved_by": self.resolved_by,
            "created_at": self.created_at
        }


class ExceptionRegistry:
    """Central repository for tracking and resolving drawing exceptions."""

    def __init__(self):
        self._exceptions: list[ExceptionRecord] = []
        self._counter: int = 1

    def record_exception(
        self,
        code: ExceptionCode,
        drawing_id: str,
        message: str,
        severity: ExceptionSeverity | None = None,
        entity_id: str | None = None,
        suggested_action: str = "",
        suggested_default: float | str | None = None
    ) -> ExceptionRecord:
        if severity is None:
            if code in (ExceptionCode.SCALE_REQUIRED, ExceptionCode.SCALE_NOT_FOUND, ExceptionCode.UNIT_REQUIRED):
                severity = ExceptionSeverity.BLOCKING
            else:
                severity = ExceptionSeverity.WARNING

        record = ExceptionRecord(
            id=f"EXC-{self._counter:04d}",
            code=code,
            drawing_id=drawing_id,
            message=message,
            severity=severity,
            entity_id=entity_id,
            suggested_action=suggested_action,
            suggested_default=suggested_default
        )
        self._exceptions.append(record)
        self._counter += 1
        return record

    def get_pending_exceptions(self) -> list[ExceptionRecord]:
        return [e for e in self._exceptions if not e.resolved]

    def get_all(self) -> list[ExceptionRecord]:
        return list(self._exceptions)

    @property
    def has_blocking_exceptions(self) -> bool:
        """Returns True if any un-resolved blocking exceptions exist."""
        return any(
            not e.resolved and (e.severity == ExceptionSeverity.BLOCKING or e.code in (
                ExceptionCode.SCALE_REQUIRED, ExceptionCode.SCALE_NOT_FOUND, ExceptionCode.UNIT_REQUIRED
            ))
            for e in self._exceptions
        )
