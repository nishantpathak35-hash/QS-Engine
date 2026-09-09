"""
QS Quantification Engine — DXF Layer Classification Profile
Maps CAD layer conventions to normalized semantic categories.
Enforces Blueprint Section 11 & Section 111.
"""

from __future__ import annotations
import re
from enum import Enum
from dataclasses import dataclass, field

class LayerCategory(str, Enum):
    WALL = "wall"
    DOOR = "door"
    WINDOW = "window"
    FLOOR_FINISH = "floor_finish"
    CEILING_FINISH = "ceiling_finish"
    FURNITURE = "furniture"
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    ANNOTATION = "annotation"
    DIMENSION = "dimension"
    HATCH = "hatch"
    IGNORED = "ignored"
    UNKNOWN = "unknown"


@dataclass
class LayerMappingProfile:
    """Configurable layer mapping dictionary and regex patterns."""
    name: str = "Standard Architectural CAD"
    exact_mappings: dict[str, LayerCategory] = field(default_factory=lambda: {
        "A-WALL": LayerCategory.WALL,
        "WALL": LayerCategory.WALL,
        "WALLS": LayerCategory.WALL,
        "PARTITION": LayerCategory.WALL,
        "A-DOOR": LayerCategory.DOOR,
        "DOOR": LayerCategory.DOOR,
        "DOORS": LayerCategory.DOOR,
        "DR": LayerCategory.DOOR,
        "A-GLAZ": LayerCategory.WINDOW,
        "WINDOW": LayerCategory.WINDOW,
        "WINDOWS": LayerCategory.WINDOW,
        "FL-FIN": LayerCategory.FLOOR_FINISH,
        "FLOORING": LayerCategory.FLOOR_FINISH,
        "FLOOR_FINISH": LayerCategory.FLOOR_FINISH,
        "A-CLNG": LayerCategory.CEILING_FINISH,
        "CEILING": LayerCategory.CEILING_FINISH,
        "F-FURN": LayerCategory.FURNITURE,
        "FURNITURE": LayerCategory.FURNITURE,
        "E-LGT": LayerCategory.ELECTRICAL,
        "ELECTRICAL": LayerCategory.ELECTRICAL,
        "P-SAN": LayerCategory.PLUMBING,
        "PLUMBING": LayerCategory.PLUMBING,
        "TEXT": LayerCategory.ANNOTATION,
        "A-ANNO": LayerCategory.ANNOTATION,
        "DIM": LayerCategory.DIMENSION,
        "DIMENSION": LayerCategory.DIMENSION,
        "DEFPOINTS": LayerCategory.IGNORED,
        "VIEWPORT": LayerCategory.IGNORED,
    })
    regex_patterns: list[tuple[re.Pattern, LayerCategory]] = field(default_factory=lambda: [
        (re.compile(r".*wall.*|.*partition.*|.*part_.*", re.IGNORECASE), LayerCategory.WALL),
        (re.compile(r".*door.*", re.IGNORECASE), LayerCategory.DOOR),
        (re.compile(r".*window.*|.*glaz.*", re.IGNORECASE), LayerCategory.WINDOW),
        (re.compile(r".*floor.*|.*tile.*|.*carpet.*", re.IGNORECASE), LayerCategory.FLOOR_FINISH),
        (re.compile(r".*ceiling.*|.*rcp.*", re.IGNORECASE), LayerCategory.CEILING_FINISH),
        (re.compile(r".*furn.*", re.IGNORECASE), LayerCategory.FURNITURE),
        (re.compile(r".*elec.*|.*light.*", re.IGNORECASE), LayerCategory.ELECTRICAL),
        (re.compile(r".*anno.*|.*text.*|.*room.*", re.IGNORECASE), LayerCategory.ANNOTATION),
        (re.compile(r".*dim.*", re.IGNORECASE), LayerCategory.DIMENSION),
    ])

    use_llm_fallback: bool = True

    def classify_layer(self, layer_name: str) -> LayerCategory:
        """Determines semantic category from CAD layer name, with LLM fallback for ambiguous layers."""
        clean_name = layer_name.strip().upper()
        if clean_name in self.exact_mappings:
            return self.exact_mappings[clean_name]

        for pattern, category in self.regex_patterns:
            if pattern.match(layer_name):
                return category

        # Blueprint Section 54: Invoke LLM only when rule & regex matching cannot classify
        if self.use_llm_fallback:
            try:
                from core.ai.factory import LLMProviderFactory
                provider = LLMProviderFactory.get_provider()
                ai_result = provider.classify_layer(layer_name)
                if ai_result.confidence >= 0.70:
                    try:
                        resolved_cat = LayerCategory(ai_result.category.lower())
                        # Cache resolved classification for fast lookup across drawing
                        self.exact_mappings[clean_name] = resolved_cat
                        return resolved_cat
                    except ValueError:
                        pass
            except Exception:
                pass

        return LayerCategory.UNKNOWN

# Alias for backwards compatibility
LayerClassifier = LayerMappingProfile

