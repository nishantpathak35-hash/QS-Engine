"""
QS Quantification Engine — Core Exception Hierarchy
Strict domain exceptions preventing silent fallbacks and fake quantities.
"""

class QSEngineException(Exception):
    """Base exception for all QS Engine errors."""
    pass


class ScaleRequiredError(QSEngineException):
    """Raised when drawing scale cannot be determined with mathematical certainty.
    Prevents generating fake or uncalibrated quantities."""
    def __init__(self, message: str = "Drawing scale is required before calculation can proceed."):
        super().__init__(message)


class UnitRequiredError(QSEngineException):
    """Raised when drawing units ($INSUNITS) are unspecified (0 / Unitless) and no
    user-approved unit assumption is configured."""
    def __init__(self, message: str = "Drawing units are unspecified ($INSUNITS=0). Explicit unit required."):
        super().__init__(message)


class UnsupportedUnitError(QSEngineException):
    """Raised when drawing units ($INSUNITS) use an unsupported unit code.
    Prevents silent fallback to 1.0."""
    def __init__(self, message: str = "Drawing has unsupported unit code. Supported: inches(1), feet(2), mm(4), cm(5), m(6)."):
        super().__init__(message)


class RoomBoundaryOpenError(QSEngineException):
    """Raised when an interior room polygon is not closed beyond acceptable tolerance."""
    def __init__(self, room_name: str, gap_mm: float, location: tuple[float, float]):
        self.room_name = room_name
        self.gap_mm = gap_mm
        self.location = location
        super().__init__(
            f"Room boundary for '{room_name}' is open (gap: {gap_mm:.2f}mm at {location}). "
            f"Human review required."
        )


class MissingAttributeError(QSEngineException):
    """Raised when an essential physical property is missing."""
    def __init__(self, entity_id: str, attribute_name: str, suggested_default: float | None = None):
        self.entity_id = entity_id
        self.attribute_name = attribute_name
        self.suggested_default = suggested_default
        super().__init__(
            f"Entity '{entity_id}' is missing required attribute '{attribute_name}'. "
            f"Suggested default: {suggested_default}"
        )


class MissingHeightError(QSEngineException):
    """Raised when ceiling or wall height is required for 3D/vertical measurement but unavailable."""
    def __init__(self, entity_id: str, element_type: str = "wall"):
        self.entity_id = entity_id
        self.element_type = element_type
        super().__init__(f"Height for {element_type} '{entity_id}' is missing. Cannot assume without confirmation.")


class MissingOpeningDimensionError(QSEngineException):
    """Raised when an opening's width or height is missing and no user default is approved."""
    def __init__(self, opening_id: str, dimension_type: str = "width"):
        self.opening_id = opening_id
        self.dimension_type = dimension_type
        super().__init__(f"Opening '{opening_id}' is missing required dimension '{dimension_type}'.")


class AmbiguousRoomLabelError(QSEngineException):
    """Raised when multiple conflicting room labels exist within the same polygon boundary."""
    def __init__(self, room_id: str, candidate_labels: list[str]):
        self.room_id = room_id
        self.candidate_labels = candidate_labels
        super().__init__(f"Room '{room_id}' contains multiple conflicting room labels: {candidate_labels}.")


class UnknownBlockError(QSEngineException):
    """Raised when an unmapped CAD block cannot be classified into doors, furniture, or fixtures."""
    def __init__(self, block_name: str, layer: str, location: tuple[float, float]):
        self.block_name = block_name
        self.layer = layer
        self.location = location
        super().__init__(f"Unknown CAD block '{block_name}' on layer '{layer}' at {location}. Human review required.")


class UnknownFinishError(QSEngineException):
    """Raised when an unrecognized finish tag/code has no mapping in project profile."""
    def __init__(self, finish_code: str, location: str):
        self.finish_code = finish_code
        self.location = location
        super().__init__(f"Unrecognized finish code '{finish_code}' in '{location}'.")


class LowConfidenceDoorError(QSEngineException):
    """Raised when a candidate door opening cannot be geometrically associated with a host wall."""
    def __init__(self, opening_id: str, location: tuple[float, float]):
        self.opening_id = opening_id
        self.location = location
        super().__init__(f"Door opening '{opening_id}' at {location} has no host wall within tolerance.")


class RasterProcessingNotSupportedError(QSEngineException):
    """Raised when a scanned/raster drawing is passed to vector-only pipelines."""
    def __init__(self, filename: str):
        super().__init__(
            f"Drawing '{filename}' is a raster/scanned image. Raster processing is currently "
            f"not supported. RASTER_PROCESSING_NOT_SUPPORTED."
        )


class RuleEvaluationError(QSEngineException):
    """Raised when a QS rule formula fails validation or execution."""
    pass
