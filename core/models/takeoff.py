"""
QS Quantification Engine — Takeoff & Audit Trail Data Model
Enforces Blueprint Section 37 (Lineage & Audit Trail) and Section 80 (Status Model).
Every calculated number MUST be explainable with source entities and formula strings.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from core.units import DisplayUnit
from core.models.semantics import EntityStatus

@dataclass
class TakeoffLineItem:
    """Individual auditable QS measurement line item."""
    id: str
    item_code: str
    description: str
    location: str
    quantity: float
    unit: DisplayUnit
    formula: str
    source_entities: list[str] = field(default_factory=list)
    confidence: float = 0.95
    status: EntityStatus = EntityStatus.AUTO_MEASURED
    rule_id: str = "DEFAULT"
    rule_version: str = "1.0.0"
    calculator: str = "is1200.generic"
    measurement_method: str = "IS 1200"
    deductions: list[dict] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    wastage_percent: float = 0.0
    gross_quantity: float | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        unit_val = getattr(self.unit, "value", str(self.unit))
        status_val = getattr(self.status, "value", str(self.status))
        is_nos = (self.unit == DisplayUnit.NOS) or (unit_val.lower() in ("nos", "nr", "no"))

        g_qty = self.gross_quantity
        if g_qty is None:
            if is_nos and self.wastage_percent > 0:
                import math
                g_qty = float(math.ceil(self.quantity * (1.0 + self.wastage_percent)))
            else:
                g_qty = round(self.quantity * (1.0 + self.wastage_percent), 2)

        return {
            "id": self.id,
            "item_code": self.item_code,
            "description": self.description,
            "location": self.location,
            "quantity": round(self.quantity, 2),
            "net_quantity": round(self.quantity, 2),
            "wastage_percent": round(self.wastage_percent, 3),
            "wastage_quantity": round(max(0.0, g_qty - self.quantity), 2),
            "gross_quantity": round(g_qty, 2),
            "raw_quantity": self.quantity,
            "unit": unit_val,
            "formula": self.formula,
            "source_entities": self.source_entities,
            "confidence": round(self.confidence, 3),
            "status": status_val,
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "calculator": self.calculator,
            "measurement_method": self.measurement_method,
            "deductions": self.deductions,
            "assumptions": self.assumptions,
            "created_at": self.created_at
        }


@dataclass
class TakeoffSummary:
    """Consolidated project/drawing takeoff report."""
    drawing_id: str
    drawing_number: str
    revision: str
    items: list[TakeoffLineItem] = field(default_factory=list)
    exceptions: list[dict] = field(default_factory=list)
    base_measurements: dict[str, Any] = field(default_factory=dict)

    def total_by_item(self) -> dict[str, dict]:
        """Aggregates totals across all rooms by item code, providing Net and Gross Procurement quantities."""
        import math
        totals = {}
        for item in self.items:
            unit_val = getattr(item.unit, "value", str(item.unit))
            is_nos = (item.unit == DisplayUnit.NOS) or (unit_val.lower() in ("nos", "nr", "no"))

            if item.item_code not in totals:
                totals[item.item_code] = {
                    "description": item.description,
                    "total_quantity": 0.0,
                    "net_quantity": 0.0,
                    "wastage_percent": item.wastage_percent,
                    "wastage_quantity": 0.0,
                    "gross_quantity": 0.0,
                    "unit": unit_val,
                    "count": 0
                }
            totals[item.item_code]["total_quantity"] += item.quantity
            totals[item.item_code]["net_quantity"] += item.quantity

            if item.gross_quantity is not None:
                g_qty = item.gross_quantity
            elif is_nos and item.wastage_percent > 0:
                g_qty = float(math.ceil(item.quantity * (1.0 + item.wastage_percent)))
            else:
                g_qty = item.quantity * (1.0 + item.wastage_percent)

            totals[item.item_code]["gross_quantity"] += g_qty
            totals[item.item_code]["count"] += 1

        for code in totals:
            totals[code]["total_quantity"] = round(totals[code]["total_quantity"], 2)
            totals[code]["net_quantity"] = round(totals[code]["net_quantity"], 2)
            totals[code]["gross_quantity"] = round(totals[code]["gross_quantity"], 2)
            totals[code]["wastage_quantity"] = round(max(0.0, totals[code]["gross_quantity"] - totals[code]["net_quantity"]), 2)
        return totals

    def to_dict(self) -> dict:
        return {
            "drawing_id": self.drawing_id,
            "drawing_number": self.drawing_number,
            "revision": self.revision,
            "items": [item.to_dict() for item in self.items],
            "totals": self.total_by_item(),
            "exceptions": self.exceptions,
            "base_measurements": self.base_measurements
        }
