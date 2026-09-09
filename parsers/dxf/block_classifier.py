"""
QS Quantification Engine — Block Classification Hierarchy
Categorizes DXF Blocks into Doors, Windows, Furniture, Fixtures, and Unknowns.
Enforces the strict rule: NEVER assume BLOCK = DOOR.
"""

from __future__ import annotations
import re
from enum import Enum
from dataclasses import dataclass, field
from core.models.semantics import Opening, OpeningType, BlockInstance, EntityStatus
from core.geometry.primitives import Point2D
from parsers.dxf.reader import ExtractedBlock

class BlockCategory(str, Enum):
    DOOR = "door"
    WINDOW = "window"
    FURNITURE = "furniture"
    FIXTURE = "fixture"
    EQUIPMENT = "equipment"
    COLUMN = "column"
    UNKNOWN = "unknown"


@dataclass
class BlockClassificationResult:
    category: BlockCategory
    confidence: float
    detected_width_m: float | None = None
    tag: str | None = None
    reason: str = ""
    is_door: bool = False


@dataclass
class BlockMappingProfile:
    """Configurable layer and naming patterns for block categorization."""
    door_layers: list[str] = field(default_factory=lambda: [
        "A-DOOR", "DOOR", "DOORS", "DR", "I-DOOR", "ARCH-DOOR", "DOOR-SWING", "A-GLAZ-DOOR"
    ])
    window_layers: list[str] = field(default_factory=lambda: [
        "A-GLAZ", "WINDOW", "WINDOWS", "GLAZING", "A-WALL-GLAZ"
    ])
    furniture_layers: list[str] = field(default_factory=lambda: [
        "F-FURN", "FURNITURE", "FURN", "I-FURN", "A-FURN"
    ])
    fixture_layers: list[str] = field(default_factory=lambda: [
        "P-SANR", "PLUMBING", "FIXTURES", "SAN", "A-EQPM-SANR"
    ])

    # Regex patterns
    door_patterns: list[str] = field(default_factory=lambda: [
        r"^D[0-9]+([_-].*)?$",
        r"^DR[0-9]*([_-].*)?$",
        r".*DOOR.*",
        r".*SWING.*",
        r".*LEAF.*"
    ])
    furniture_patterns: list[str] = field(default_factory=lambda: [
        r".*WORKSTATION.*",
        r".*WS[0-9]*",
        r".*DESK.*",
        r".*CHAIR.*",
        r".*TABLE.*",
        r".*SOFA.*",
        r".*CABINET.*",
        r".*STORAGE.*",
        r".*PLANT.*",
        r".*CREDENZA.*"
    ])
    fixture_patterns: list[str] = field(default_factory=lambda: [
        r".*WC.*",
        r".*TOILET.*",
        r".*SINK.*",
        r".*BASIN.*",
        r".*URINAL.*",
        r".*SHOWER.*"
    ])


class BlockClassifier:
    """Classifies DXF blocks using a strict 5-tier hierarchy."""

    def __init__(self, profile: BlockMappingProfile | None = None, use_llm_fallback: bool = True):
        self.profile = profile or BlockMappingProfile()
        self.use_llm_fallback = use_llm_fallback

    def classify(self, block: ExtractedBlock) -> BlockClassificationResult:
        name_upper = block.name.upper()
        layer_upper = block.layer.upper()

        # Extract potential width from name or attributes
        width_m = self._extract_width(block)
        tag = self._extract_tag(block)

        # Hierarchy Tier 0: Explicit Furniture Exclusion
        # If block name contains workstation/chair/desk, it is NEVER a door regardless of layer
        for pat in self.profile.furniture_patterns:
            if re.match(pat, name_upper):
                if any(d in name_upper for d in ["DOOR", "DR", "SWING", "LEAF"]):
                    continue
                return BlockClassificationResult(
                    category=BlockCategory.FURNITURE,
                    confidence=0.98,
                    tag=tag,
                    reason=f"Block name '{block.name}' matched furniture pattern '{pat}'",
                    is_door=False
                )

        # Hierarchy Tier 0b: Explicit Fixture Exclusion
        for pat in self.profile.fixture_patterns:
            if re.match(pat, name_upper):
                if any(d in name_upper for d in ["DOOR", "DR", "SWING", "LEAF"]):
                    continue
                return BlockClassificationResult(
                    category=BlockCategory.FIXTURE,
                    confidence=0.98,
                    tag=tag,
                    reason=f"Block name '{block.name}' matched fixture pattern '{pat}'",
                    is_door=False
                )

        # Hierarchy Tier 1: Explicit Mapped Door Layer
        for d_layer in self.profile.door_layers:
            if d_layer in layer_upper:
                return BlockClassificationResult(
                    category=BlockCategory.DOOR,
                    confidence=0.95,
                    detected_width_m=width_m,
                    tag=tag or block.name,
                    reason=f"Block on explicit door layer '{block.layer}'",
                    is_door=True
                )

        # Hierarchy Tier 2: Known Door Block Name Pattern
        for pat in self.profile.door_patterns:
            if re.match(pat, name_upper):
                return BlockClassificationResult(
                    category=BlockCategory.DOOR,
                    confidence=0.92,
                    detected_width_m=width_m,
                    tag=tag or block.name,
                    reason=f"Block name '{block.name}' matched door pattern '{pat}'",
                    is_door=True
                )

        # Hierarchy Tier 3: Block Attributes Tag
        if tag and re.match(r"^D[0-9]+", tag.upper()):
            return BlockClassificationResult(
                category=BlockCategory.DOOR,
                confidence=0.90,
                detected_width_m=width_m,
                tag=tag,
                reason=f"Block attribute tag '{tag}' indicates door",
                is_door=True
            )

        # Hierarchy Tier 4: Furniture or Fixture Layer
        for f_layer in self.profile.furniture_layers:
            if f_layer in layer_upper:
                return BlockClassificationResult(
                    category=BlockCategory.FURNITURE,
                    confidence=0.90,
                    tag=tag,
                    reason=f"Block on furniture layer '{block.layer}'",
                    is_door=False
                )

        # Hierarchy Tier 4.5: LLM-Assisted Ambiguity Resolution (Blueprint Section 54/55)
        if self.use_llm_fallback:
            try:
                from core.ai.factory import LLMProviderFactory
                provider = LLMProviderFactory.get_provider()
                ai_res = provider.classify_block(block.name, block.layer, block.attributes)
                if ai_res.confidence >= 0.70 and ai_res.category != "unknown":
                    try:
                        cat = BlockCategory(ai_res.category.lower())
                        return BlockClassificationResult(
                            category=cat,
                            confidence=ai_res.confidence,
                            detected_width_m=width_m,
                            tag=tag or block.name,
                            reason=f"LLM Classification: {ai_res.reason}",
                            is_door=ai_res.is_door
                        )
                    except ValueError:
                        pass
            except Exception:
                pass

        # Hierarchy Tier 5: Unresolved -> UNKNOWN (Never guess DOOR)
        return BlockClassificationResult(
            category=BlockCategory.UNKNOWN,
            confidence=0.30,
            tag=tag,
            reason=f"Block '{block.name}' on layer '{block.layer}' does not match any known pattern",
            is_door=False
        )

    def _extract_width(self, block: ExtractedBlock) -> float | None:
        """Attempts to extract physical width from block attributes or name in meters."""
        # 1. Check attributes
        for key, val in block.attributes.items():
            if key.upper() in ("WIDTH", "DOOR_WIDTH", "W", "OPENING_WIDTH"):
                val_clean = re.sub(r"[^\d.]", "", val)
                if val_clean:
                    num = float(val_clean)
                    # If in mm (e.g. 900, 1000, 1200) -> convert to m
                    return num / 1000.0 if num > 50.0 else num

        # 2. Check name (e.g. DOOR_900 or D-1000)
        match = re.search(r"(\d{3,4})", block.name)
        if match:
            num = float(match.group(1))
            if 500 <= num <= 3000:
                return num / 1000.0

        return None

    def _extract_tag(self, block: ExtractedBlock) -> str | None:
        """Extracts mark/tag (e.g. D1, D-02)."""
        for key in ("TAG", "MARK", "DOOR_NO", "NUMBER", "ID"):
            if key in block.attributes:
                return block.attributes[key]
        return None
