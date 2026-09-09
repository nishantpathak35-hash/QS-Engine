"""
QS Quantification Engine — Semantic Model Layer
Represents interpreted construction objects before rule processing.
Forms the Single Source of Truth as defined in Blueprint Section 22.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from enum import Enum
from core.geometry.primitives import Point2D, Polygon2D

class EntityStatus(str, Enum):
    RAW_MEASURED = "raw_measured"
    AUTO_MEASURED = "auto_measured"
    REVIEW_REQUIRED = "review_required"
    VERIFIED = "verified"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    UNRESOLVED = "unresolved"
    # Aliases for compatibility
    BLOCKED = "unresolved"
    DRAFT = "raw_measured"


class OpeningType(str, Enum):
    DOOR = "door"
    WINDOW = "window"
    OPENING = "opening"


@dataclass
class Opening:
    """Represents a door or window opening hosted in a wall."""
    id: str
    opening_type: OpeningType
    door_type: str | None = None  # single_leaf, double_leaf, glass, sliding, unknown
    material: str | None = None  # wood, glass, metal, aluminum
    width_m: float | None = None
    height_m: float | None = None
    host_wall_id: str | None = None
    tag: str | None = None
    location: Point2D = field(default_factory=lambda: Point2D(0, 0))
    orientation_deg: float = 0.0
    jamb_p1: Point2D | None = None
    jamb_p2: Point2D | None = None
    detection_source: str = "layer"  # layer, block, tag, geometry, manual
    confidence: float = 0.95
    status: EntityStatus = EntityStatus.AUTO_MEASURED
    is_provisional: bool = False
    drawing_id: str | None = None
    page_number: int = 1
    page_scale: int | None = None
    width_source: str | None = None  # DRAWING, PROJECT_ASSUMPTION, SCHEDULE
    height_source: str | None = None  # DRAWING, PROJECT_ASSUMPTION, SCHEDULE

    def __post_init__(self):
        if self.opening_type == OpeningType.DOOR and self.door_type is None:
            if self.width_m is not None:
                self.door_type = "single_leaf" if self.width_m <= 1.25 else "double_leaf"


    @property
    def area_sqm(self) -> float | None:
        if self.width_m is not None and self.height_m is not None:
            return self.width_m * self.height_m
        return None

    def get_threshold_segment(self) -> tuple[Point2D, Point2D] | None:
        """Returns the start and end coordinates of the threshold line in mm."""
        if self.jamb_p1 and self.jamb_p2:
            return (self.jamb_p1, self.jamb_p2)
        if self.width_m is not None:
            rad = math.radians(self.orientation_deg)
            w_mm = self.width_m * 1000.0
            p1 = self.location
            p2 = Point2D(p1.x + w_mm * math.cos(rad), p1.y + w_mm * math.sin(rad))
            return (p1, p2)
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "opening_type": self.opening_type.value,
            "door_type": self.door_type,
            "material": self.material,
            "width_m": self.width_m,
            "width_mm": round(self.width_m * 1000.0, 1) if self.width_m is not None else None,
            "width_source": self.width_source,
            "height_m": self.height_m,
            "height_mm": round(self.height_m * 1000.0, 1) if self.height_m is not None else None,
            "height_source": self.height_source,
            "host_wall_id": self.host_wall_id,
            "tag": self.tag,
            "confidence": self.confidence,
            "status": self.status.value,
            "is_provisional": self.is_provisional
        }


@dataclass
class WallSegment:
    """Represents a centerline wall segment."""
    id: str
    start: Point2D
    end: Point2D
    thickness_mm: float = 100.0
    height_m: float | None = None  # None triggers MISSING_HEIGHT exception
    layer: str = "A-WALL"
    classification: str = "partition"
    wall_type: str = "partition"  # partition, structural, curtain, shaft
    partition_type: str | None = None  # gypsum, glass, masonry, modular
    height_source: str | None = None  # DRAWING, PROJECT_ASSUMPTION, SCHEDULE
    confidence: float = 0.95
    status: EntityStatus = EntityStatus.AUTO_MEASURED
    drawing_id: str | None = None
    page_number: int = 1
    page_scale: int | None = None

    @property
    def entity_type(self) -> str:
        return "wall"

    @property
    def length_m(self) -> float:
        return self.start.distance_to(self.end) / 1000.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "wall_type": self.wall_type,
            "partition_type": self.partition_type,
            "length_m": round(self.length_m, 3),
            "height_m": self.height_m,
            "height_source": self.height_source,
            "thickness_mm": self.thickness_mm,
            "layer": self.layer,
            "confidence": self.confidence,
            "status": self.status.value
        }


@dataclass
class Room:
    """Represents a closed spatial room region."""
    id: str
    name: str
    polygon: Polygon2D
    label_point: Point2D | None = None
    finish_code: str | None = None
    skirting_finish_code: str | None = None
    ceiling_finish_code: str | None = None
    confidence: float = 0.95
    status: EntityStatus = EntityStatus.AUTO_MEASURED
    has_uncertain_boundary: bool = False
    drawing_id: str | None = None
    page_number: int = 1
    page_scale: int | None = None
    boundary_source: str = "wall_detector"

    @property
    def gross_area_sqm(self) -> float:
        return self.polygon.gross_area_mm2 * 1e-6

    @property
    def net_area_sqm(self) -> float:
        return self.polygon.net_area_mm2 * 1e-6

    @property
    def perimeter_m(self) -> float:
        return self.polygon.perimeter_mm * 1e-3

    @property
    def gross_perimeter_m(self) -> float:
        return self.perimeter_m

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "net_area_sqm": round(self.net_area_sqm, 3),
            "perimeter_m": round(self.perimeter_m, 3),
            "finish_code": self.finish_code,
            "skirting_finish_code": self.skirting_finish_code,
            "ceiling_finish_code": self.ceiling_finish_code,
            "confidence": round(self.confidence, 3),
            "status": self.status.value,
            "boundary_source": self.boundary_source,
            "has_uncertain_boundary": self.has_uncertain_boundary
        }


@dataclass
class BlockInstance:
    """Represents an extracted CAD block/symbol (furniture, fixtures, doors)."""
    id: str
    block_name: str
    category: str
    insertion_point: Point2D
    rotation_deg: float = 0.0
    layer: str = "0"
    attributes: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.99
    status: EntityStatus = EntityStatus.AUTO_MEASURED
