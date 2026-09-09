"""
QS Quantification Engine — API Contracts & Pydantic Schemas
Defines strictly validated request and response payloads for Construct-O-Genie integration.
Enforces Blueprint Section 45 (API Design).
"""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    status: str = "healthy"
    engine_version: str = "1.0.0"
    deterministic_core: bool = True
    ai_api_marginal_cost: str = "₹0 (100% Local)"


class DrawingUploadResponse(BaseModel):
    drawing_id: str
    filename: str
    file_type: str
    page_count: int
    message: str = "Drawing successfully uploaded and classified."


class TakeoffItemSchema(BaseModel):
    id: str
    item_code: str
    description: str
    location: str
    quantity: float
    unit: str
    formula: str
    source_entities: list[str] = Field(default_factory=list)
    confidence: float
    status: str
    rule_id: str
    rule_version: str = "1.0.0"
    calculator: str = "is1200.generic"
    measurement_method: str = "IS 1200"
    deductions: list[dict] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    net_quantity: float | None = None
    wastage_percent: float | None = 0.0
    wastage_quantity: float | None = 0.0
    gross_quantity: float | None = None


class TakeoffTotalSchema(BaseModel):
    description: str
    total_quantity: float
    unit: str
    count: int
    net_quantity: float | None = None
    wastage_percent: float | None = 0.0
    wastage_quantity: float | None = 0.0
    gross_quantity: float | None = None


class TakeoffResponse(BaseModel):
    drawing_id: str
    drawing_number: str
    revision: str
    items: list[TakeoffItemSchema]
    totals: dict[str, TakeoffTotalSchema]
    exceptions: list[dict] = Field(default_factory=list)
    base_measurements: dict[str, Any] = Field(default_factory=dict)
    geometry: dict[str, Any] = Field(default_factory=dict)
    priced_estimate: dict[str, Any] | None = None



class ExceptionSchema(BaseModel):
    id: str
    code: str
    drawing_id: str
    message: str
    suggested_action: str
    resolved: bool
    resolution_value: float | str | None = None


class ResolveExceptionRequest(BaseModel):
    resolution_value: float | str
    user_id: str = "estimator"
