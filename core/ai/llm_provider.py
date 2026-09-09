"""
QS Quantification Engine — Free LLM Provider & Task Contracts
Enforces Blueprint Section 54 (Why LLM Should Be Last), Section 55 (Task Contract),
Section 56 (Never Let AI Invent Dimensions), and Section 106 (Provider Interface).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class AITaskType(str, Enum):
    CLASSIFY_LAYER = "classify_layer"
    CLASSIFY_BLOCK = "classify_block"
    CLASSIFY_ANNOTATION = "classify_annotation"


class LayerClassificationOutput(BaseModel):
    """Constrained schema for CAD layer categorization by LLM."""
    layer_name: str
    category: str = Field(description="One of: wall, door, window, floor_finish, ceiling_finish, furniture, electrical, plumbing, annotation, dimension, ignored, unknown")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    reason: str = Field(default="", description="Short architectural reasoning")


class BlockClassificationOutput(BaseModel):
    """Constrained schema for CAD block categorization by LLM."""
    block_name: str
    category: str = Field(description="One of: door, window, furniture, fixture, equipment, column, unknown")
    is_door: bool = Field(default=False)
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(default="")


class AnnotationClassificationOutput(BaseModel):
    """Constrained schema for ambiguous drawing text notes."""
    raw_text: str
    semantic_type: str = Field(description="One of: room_name, finish_code, dimension, note, unknown")
    normalized_value: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)


class BaseLLMProvider(ABC):
    """Abstract LLM Provider interface supporting 100% free / local inference."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the LLM provider (e.g. 'gemini-free', 'ollama-local', 'deterministic-fallback')."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Checks if the provider is currently reachable and configured."""
        pass

    @abstractmethod
    def classify_layer(self, layer_name: str, sample_entities: Optional[list[str]] = None) -> LayerClassificationOutput:
        """Classifies an ambiguous CAD layer name."""
        pass

    @abstractmethod
    def classify_block(self, block_name: str, layer: str, attributes: Optional[dict[str, Any]] = None) -> BlockClassificationOutput:
        """Classifies an ambiguous CAD block name."""
        pass

    @abstractmethod
    def classify_annotation(self, text: str) -> AnnotationClassificationOutput:
        """Extracts semantics from ambiguous text annotations."""
        pass
