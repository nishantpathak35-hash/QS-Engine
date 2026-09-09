"""
QS Quantification Engine — Revision & Delta Data Models
Enforces Blueprint Section 38 (Revision Management) & Section 39 (Geometry Difference Engine).
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

class ChangeType(str, Enum):
    UNCHANGED = "unchanged"
    MODIFIED = "modified"
    ADDED = "added"
    REMOVED = "removed"
    UNCERTAIN_MATCH = "uncertain_match"


@dataclass
class QuantityDelta:
    item_code: str
    description: str
    location: str
    baseline_qty: float
    revised_qty: float
    delta_qty: float
    delta_percentage: float | None
    unit: str
    change_type: ChangeType
    match_confidence: float = 1.0
    spatial_similarity: float | None = None

    def to_dict(self) -> dict:
        return {
            "item_code": self.item_code,
            "description": self.description,
            "location": self.location,
            "baseline_qty": round(self.baseline_qty, 2),
            "revised_qty": round(self.revised_qty, 2),
            "delta_qty": round(self.delta_qty, 2),
            "delta_percentage": round(self.delta_percentage, 1) if self.delta_percentage is not None else None,
            "unit": self.unit,
            "change_type": self.change_type.value,
            "match_confidence": round(self.match_confidence, 2),
            "spatial_similarity": round(self.spatial_similarity, 3) if self.spatial_similarity is not None else None
        }


@dataclass
class RevisionComparisonResult:
    baseline_drawing_id: str
    revised_drawing_id: str
    baseline_revision: str
    revised_revision: str
    deltas: list[QuantityDelta] = field(default_factory=list)
    compared_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def added_items(self) -> list[QuantityDelta]:
        return [d for d in self.deltas if d.change_type == ChangeType.ADDED]

    @property
    def removed_items(self) -> list[QuantityDelta]:
        return [d for d in self.deltas if d.change_type == ChangeType.REMOVED]

    @property
    def modified_items(self) -> list[QuantityDelta]:
        return [d for d in self.deltas if d.change_type == ChangeType.MODIFIED]

    @property
    def unchanged_items(self) -> list[QuantityDelta]:
        return [d for d in self.deltas if d.change_type == ChangeType.UNCHANGED]

    @property
    def net_area_delta_sqm(self) -> float:
        """Sum of all flooring/area deltas in sqm."""
        return sum(d.delta_qty for d in self.deltas if d.unit.lower() == "sqm")

    def to_dict(self) -> dict:
        return {
            "baseline_drawing_id": self.baseline_drawing_id,
            "revised_drawing_id": self.revised_drawing_id,
            "baseline_revision": self.baseline_revision,
            "revised_revision": self.revised_revision,
            "summary": {
                "total_items_compared": len(self.deltas),
                "modified_count": len(self.modified_items),
                "added_count": len(self.added_items),
                "removed_count": len(self.removed_items),
                "unchanged_count": len(self.unchanged_items),
                "net_area_delta_sqm": round(self.net_area_delta_sqm, 2)
            },
            "deltas": [d.to_dict() for d in self.deltas],
            "compared_at": self.compared_at
        }
