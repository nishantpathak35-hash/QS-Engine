"""
QS Quantification Engine — Rule Schema & Profile Validation Layer
Enforces Blueprint Section 23, Section 24, and Sprint 1 Production Hardening:
- Strict Pydantic model validation of YAML profiles.
- Calculator presence & compatibility checks.
- Match policy & cardinality enforcement.
- Unit validity and rule ID uniqueness checks.
"""

from __future__ import annotations
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class MatchPolicy(str, Enum):
    EXCLUSIVE = "exclusive"
    ADDITIVE = "additive"


SUPPORTED_UNITS = {"sqm", "m2", "m", "rm", "lm", "nos", "no", "nr", "cum", "m3", "kg", "tonne", "t"}
VALID_SOURCE_ENTITIES = {"room", "wall", "opening", "door", "window", "finish_region", "polyline", "block", "entities"}


class RuleValidationError(Exception):
    """Raised when a YAML rule profile violates structural or semantic schemas."""
    pass


class RuleConfigSchema(BaseModel):
    """Strict schema for an individual QS measurement rule."""
    id: str = Field(..., alias="rule_id", description="Unique identifier for the rule")
    item_code: str = Field(..., min_length=1, description="Standard BOQ item code (e.g. FL-01, SK-01, PT-01)")
    category: str | None = None
    description: str | None = None
    unit: str = Field(..., description="Measurement unit (sqm, m, rm, nos, etc.)")
    source_entity: str = Field(..., alias="target", description="Target entity type (room, wall, opening, etc.)")
    calculator: str = Field(..., min_length=1, description="Registered calculator identifier")
    applies_when: dict[str, Any] = Field(default_factory=dict, description="Applicability filter attributes")
    match_policy: MatchPolicy = Field(default=MatchPolicy.EXCLUSIVE, description="Cardinality policy (exclusive or additive)")
    required_attributes: list[str] = Field(default_factory=list)
    deduct_openings: bool = True
    deduct_voids_over_sqm: float | None = None
    deduct_openings_over_sqm: float | None = None
    rounding: int = Field(default=2, ge=0, le=6)
    standard: str = "IS 1200"
    formula_template: str | None = None
    description_template: str | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        norm = v.lower().strip()
        if norm not in SUPPORTED_UNITS:
            raise ValueError(f"Unsupported measurement unit '{v}'. Supported: {sorted(SUPPORTED_UNITS)}")
        return norm

    @field_validator("source_entity")
    @classmethod
    def validate_source_entity(cls, v: str) -> str:
        norm = v.lower().strip().rstrip("s")
        valid_normalized = {e.rstrip("s") for e in VALID_SOURCE_ENTITIES}
        if norm not in valid_normalized and v.lower() not in VALID_SOURCE_ENTITIES:
            raise ValueError(f"Invalid source_entity '{v}'. Supported: {sorted(VALID_SOURCE_ENTITIES)}")
        return v.lower().strip()

    @field_validator("calculator")
    @classmethod
    def validate_calculator_exists(cls, v: str) -> str:
        from qs.calculator_registry import CalculatorRegistry
        if not CalculatorRegistry.is_registered(v):
            raise ValueError(f"UNKNOWN_CALCULATOR: Calculator '{v}' is not registered in CalculatorRegistry.")
        return v

    @model_validator(mode="after")
    def validate_calculator_compatibility(self) -> RuleConfigSchema:
        from qs.calculator_registry import CalculatorRegistry
        calc_name = self.calculator
        source = self.source_entity
        if not CalculatorRegistry.validate_compatibility(calc_name, source):
            supported = CalculatorRegistry.get_supported_entities(calc_name)
            raise ValueError(
                f"Incompatible calculator '{calc_name}' for source entity '{source}'. "
                f"Calculator supports: {supported}"
            )
        return self


class RuleProfileSchema(BaseModel):
    """Strict schema for a complete loaded QS rule profile."""
    profile_id: str
    name: str | None = None
    version: str = "1.0.0"
    standard: str = "IS 1200"
    rules: list[RuleConfigSchema]
    material_mapping: dict[str, Any] = Field(default_factory=dict)
    ceiling_mapping: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

    @field_validator("rules")
    @classmethod
    def validate_unique_rule_ids(cls, rules: list[RuleConfigSchema]) -> list[RuleConfigSchema]:
        seen_ids = set()
        duplicates = []
        for r in rules:
            if r.id in seen_ids:
                duplicates.append(r.id)
            seen_ids.add(r.id)
        if duplicates:
            raise ValueError(f"Duplicate rule IDs found in profile: {duplicates}")
        return rules

    @classmethod
    def validate_raw_profile(cls, raw: dict[str, Any]) -> RuleProfileSchema:
        """Validates a raw YAML dictionary, raising RuleValidationError on issues."""
        try:
            return cls(**raw)
        except Exception as err:
            raise RuleValidationError(f"Rule profile schema validation failed: {err}") from err
