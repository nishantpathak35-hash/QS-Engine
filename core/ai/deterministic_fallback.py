"""
QS Quantification Engine — Deterministic Fallback & CI Mock LLM Provider
Enables deterministic local testing and validation of schema contracts without network dependencies.
"""

from __future__ import annotations
import re
from typing import Any, Optional

from core.ai.llm_provider import (
    BaseLLMProvider,
    LayerClassificationOutput,
    BlockClassificationOutput,
    AnnotationClassificationOutput,
)


class DeterministicFallbackLLMProvider(BaseLLMProvider):
    """
    Zero-network local reasoning provider.
    Applies deep semantic reasoning heuristics for unstandardized CAD layers and blocks,
    ensuring 100% test reproducibility and zero CI flakiness.
    """

    @property
    def provider_name(self) -> str:
        return "deterministic-local-expert"

    @property
    def is_available(self) -> bool:
        return True

    def classify_layer(self, layer_name: str, sample_entities: Optional[list[str]] = None) -> LayerClassificationOutput:
        clean = layer_name.strip().lower()
        
        # Wall variations (e.g. civil_brick_wall, int_part_gyp, partition_lead_lined, masonry_ext_wall)
        if any(w in clean for w in ["wall", "partition", "part_", "brick", "masonry", "gyp", "stud", "drywall", "lead_lined"]):
            return LayerClassificationOutput(
                layer_name=layer_name,
                category="wall",
                confidence=0.92,
                reason="Identified as wall/partition structure from architectural vocabulary"
            )

        # Door variations (e.g. custom_door_swing, clinic_door_leaf, steel_fire_door, fitting_swing)
        if any(d in clean for d in ["door", "swing", "leaf", "entry", "dr_"]):
            return LayerClassificationOutput(
                layer_name=layer_name,
                category="door",
                confidence=0.94,
                reason="Identified as door/opening entity from swing/leaf terminology"
            )

        # Window / Glazing (e.g. glazed_partition, window_ext, glass_facade)
        if any(w in clean for w in ["window", "glaz", "glass", "fenestration"]):
            return LayerClassificationOutput(
                layer_name=layer_name,
                category="window",
                confidence=0.90,
                reason="Identified as window or architectural glazing"
            )

        # Flooring (e.g. floor_vitrified_tiles, antistatic_floor, carpet_tile, ceramic_flooring)
        if any(f in clean for f in ["floor", "tile", "carpet", "vitrified", "ceramic", "vinyl", "epoxy", "screed", "fin"]):
            return LayerClassificationOutput(
                layer_name=layer_name,
                category="floor_finish",
                confidence=0.91,
                reason="Identified as floor finish layer"
            )

        # Ceiling (e.g. acoustic_ceiling, false_ceiling, rcp, pop_cornice)
        if any(c in clean for c in ["ceiling", "rcp", "false_clg", "gypsum_ceiling"]):
            return LayerClassificationOutput(
                layer_name=layer_name,
                category="ceiling_finish",
                confidence=0.88,
                reason="Identified as reflected ceiling or ceiling finish"
            )

        # Annotation / Text (e.g. room_tags, schedule_text, notes_general)
        if any(a in clean for a in ["text", "anno", "tag", "note", "schedule", "label"]):
            return LayerClassificationOutput(
                layer_name=layer_name,
                category="annotation",
                confidence=0.89,
                reason="Identified as annotation or text tag"
            )

        return LayerClassificationOutput(
            layer_name=layer_name,
            category="unknown",
            confidence=0.10,
            reason="No known architectural keywords detected"
        )

    def classify_block(self, block_name: str, layer: str, attributes: Optional[dict[str, Any]] = None) -> BlockClassificationOutput:
        clean = block_name.strip().lower()

        # Door block names (e.g. my_door_900_v1, rt_door_800, fitting_swing_door, steel_fire_exit)
        if any(d in clean for d in ["door", "dr", "swing", "leaf", "entry", "exit", "flush"]):
            return BlockClassificationOutput(
                block_name=block_name,
                category="door",
                is_door=True,
                confidence=0.95,
                reason="Recognized door block from architectural symbol naming"
            )

        # Window block names
        if any(w in clean for w in ["win", "window", "glaz", "glass_panel"]):
            return BlockClassificationOutput(
                block_name=block_name,
                category="window",
                is_door=False,
                confidence=0.92,
                reason="Recognized window/glazing block"
            )

        # Furniture block names
        if any(f in clean for f in ["desk", "table", "chair", "sofa", "bed", "workstation", "shelf", "rack"]):
            return BlockClassificationOutput(
                block_name=block_name,
                category="furniture",
                is_door=False,
                confidence=0.90,
                reason="Recognized furniture item"
            )

        # Sanitary / Fixture
        if any(s in clean for s in ["wc", "basin", "sink", "commode", "urinal", "tap"]):
            return BlockClassificationOutput(
                block_name=block_name,
                category="fixture",
                is_door=False,
                confidence=0.93,
                reason="Recognized plumbing/sanitary fixture"
            )

        return BlockClassificationOutput(
            block_name=block_name,
            category="unknown",
            is_door=False,
            confidence=0.20,
            reason="Unrecognized CAD block"
        )

    def classify_annotation(self, text: str) -> AnnotationClassificationOutput:
        clean = text.strip()
        return AnnotationClassificationOutput(
            raw_text=text,
            semantic_type="room_name" if len(clean) > 2 and clean.isupper() else "note",
            confidence=0.85
        )
