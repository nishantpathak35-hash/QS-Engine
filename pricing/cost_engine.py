"""
QS Quantification Engine — Cost Estimation & Rate Analysis Engine
Transforms physical & semantic takeoff quantities into an industry-standard Priced BOQ.
Enforces IS 1200 / POMI trade rate analysis, contractor markups, and GST calculations.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from collections import defaultdict

from core.models.takeoff import TakeoffSummary, TakeoffLineItem
from core.units import DisplayUnit


class FitoutGrade(str, Enum):
    STANDARD = "standard"          # Grade-B+ / Standard Commercial Fitout (1.0x)
    ECONOMY = "economy"            # Budget / Value Commercial Fitout (0.75x)
    GRADE_A_LUXURY = "grade_a"     # Grade-A / MNC Luxury Fitout (1.45x)


@dataclass
class TradeUnitRate:
    """Detailed unit rate breakdown for a specific BOQ item."""
    item_code: str
    description: str
    unit: str
    material_rate_inr: float
    labor_rate_inr: float
    machinery_rate_inr: float = 0.0

    @property
    def total_unit_rate_inr(self) -> float:
        return self.material_rate_inr + self.labor_rate_inr + self.machinery_rate_inr


# Industry Standard Indian Commercial Fitout Baseline Rates (CPWD / Delhi Schedule of Rates / Tier-1 Metro Fitouts)
BASELINE_RATES: dict[str, TradeUnitRate] = {
    # Flooring
    "FL-01": TradeUnitRate("FL-01", "Vitrified Tile / Italian Marble Flooring", "sqm", 1150.0, 450.0, 50.0), # ₹1650/m²
    "FL-02": TradeUnitRate("FL-02", "500x500mm Modular Nylon Carpet Tiles w/ Cushion Backing", "sqm", 1250.0, 350.0, 50.0), # ₹1650/m²
    "FL-03": TradeUnitRate("FL-03", "2mm Heterogeneous Antibacterial Heavy Duty Vinyl Flooring", "sqm", 1400.0, 400.0, 50.0), # ₹1850/m²
    "FL-04": TradeUnitRate("FL-04", "Anti-Skid Vitrified Tile Flooring (Wet Areas / Pantry)", "sqm", 1100.0, 450.0, 50.0), # ₹1600/m²
    "FL-05": TradeUnitRate("FL-05", "Heavy Duty Anti-Static Raised Access Flooring", "sqm", 2800.0, 800.0, 100.0), # ₹3700/m²
    "FL-RAW": TradeUnitRate("FL-RAW", "Standard Commercial Flooring & Screed", "sqm", 1150.0, 450.0, 50.0),
    # False Ceiling
    "CL-01": TradeUnitRate("CL-01", "12.5mm Gypsum Board False Ceiling w/ GI Framework", "sqm", 850.0, 350.0, 50.0), # ₹1250/m²
    "CL-RAW": TradeUnitRate("CL-RAW", "Commercial Gypsum / Grid False Ceiling", "sqm", 850.0, 350.0, 50.0),
    # Partitions
    "PT-01": TradeUnitRate("PT-01", "100mm Double Skin Gypsum Partition w/ 50mm Rockwool", "sqm", 1550.0, 600.0, 50.0), # ₹2200/m²
    "PT-02": TradeUnitRate("PT-02", "12mm Toughened Frameless Glass Partition", "sqm", 3200.0, 650.0, 50.0), # ₹3900/m²
    "PT-RAW": TradeUnitRate("PT-RAW", "Standard Interior Partition Wall", "m", 2800.0, 800.0, 0.0),
    # Skirting
    "SK-01": TradeUnitRate("SK-01", "100mm Matching Skirting with Edge Polish", "m", 220.0, 130.0, 0.0), # ₹350/m
    # Lighting Fixtures
    "LT-01": TradeUnitRate("LT-01", "3' Linear LED Fixture 24W w/ Suspension Profile", "nos", 1850.0, 550.0, 0.0), # ₹2400/Nos
    "LT-02": TradeUnitRate("LT-02", "5' Linear LED Fixture 40W w/ Suspension Profile", "nos", 2550.0, 650.0, 0.0), # ₹3200/Nos
    "LT-03": TradeUnitRate("LT-03", "4' Linear LED Fixture 36W w/ Suspension Profile", "nos", 2200.0, 600.0, 0.0), # ₹2800/Nos
    "LT-04": TradeUnitRate("LT-04", "8' Linear LED Fixture 60W Continuous Suspension Run", "nos", 3950.0, 850.0, 0.0), # ₹4800/Nos
    "LT-05": TradeUnitRate("LT-05", "6\" DIA Concealed Recessed LED Downlight 15W", "nos", 750.0, 200.0, 0.0), # ₹950/Nos
    "LT-06": TradeUnitRate("LT-06", "4\" DIA Cylindrical Hanging Pendant Fixture 12W", "nos", 1650.0, 450.0, 0.0), # ₹2100/Nos
    "LT-07": TradeUnitRate("LT-07", "Architectural Decorative Feature Fixture", "nos", 5200.0, 1300.0, 0.0), # ₹6500/Nos
    "LT-08": TradeUnitRate("LT-08", "Director's Cabin Premium Executive Chandelier / Rosette", "nos", 15500.0, 3000.0, 0.0), # ₹18500/Nos
    # Furniture & Workstations
    "FN-01": TradeUnitRate("FN-01", "Modular Linear / Cluster Workstation (1200x600 Desk + Pedestal)", "nos", 10800.0, 1700.0, 0.0), # ₹12500/Seat
    "FN-01B": TradeUnitRate("FN-01B", "PA / Associate Modular Workstation (1050x600 Desk + Pedestal)", "nos", 9800.0, 1500.0, 0.0), # ₹11300/Seat
    "FN-02": TradeUnitRate("FN-02", "Executive Conference Seating & Meeting Table Suite", "nos", 38000.0, 7000.0, 0.0), # ₹45000/Set
    "FN-02M": TradeUnitRate("FN-02M", "Meeting Room Seating & Table Suite (4-6 Seater)", "nos", 24000.0, 4500.0, 0.0), # ₹28500/Set
    "FN-03": TradeUnitRate("FN-03", "Director / Manager Executive Suite (Desk + Credenza + Chairs)", "nos", 55000.0, 10000.0, 0.0), # ₹65000/Set
    "FN-04": TradeUnitRate("FN-04", "Dry Pantry Service Counter w/ Solid Surface Top & Sink", "nos", 32000.0, 6000.0, 0.0), # ₹38000/Set
    # Millwork & Storage
    "MW-01": TradeUnitRate("MW-01", "Full Height Storage (F.H.S.) in Marine Ply & Laminate", "m", 11500.0, 3000.0, 0.0), # ₹14500/rm
    "MW-02": TradeUnitRate("MW-02", "Overhead Storage (O.H.S.) in Marine Ply & Laminate", "m", 7200.0, 1800.0, 0.0), # ₹9000/rm
    "MW-03": TradeUnitRate("MW-03", "Modular Planter / Storage Trough Box with Liner", "m", 4200.0, 1200.0, 0.0), # ₹5400/rm
    "MW-04": TradeUnitRate("MW-04", "Ledge / Banquet Seating with Cushioning & Commercial Ply", "m", 3800.0, 1000.0, 0.0), # ₹4800/rm
    # Glazing & Glass Partitions
    "GL-01": TradeUnitRate("GL-01", "10-12mm Acoustic Toughened Glass Partition w/ Slim Track", "m", 7500.0, 1800.0, 0.0), # ₹9300/rm
    # Doors
    "DR-01": TradeUnitRate("DR-01", "Flush Door Leaf w/ Laminate Finish & Hardware", "nos", 8500.0, 2500.0, 0.0),
    "DR-02": TradeUnitRate("DR-02", "12mm Toughened Glass Door w/ Patch Fittings & Floor Spring", "nos", 14500.0, 3500.0, 0.0),
    "DR-GL": TradeUnitRate("DR-GL", "12mm Frameless Toughened Glass Swing Door w/ Floor Spring", "nos", 14500.0, 3500.0, 0.0),
    "DR-MD": TradeUnitRate("DR-MD", "Main Entrance Double Leaf Glass Door Pair w/ Access Control", "nos", 28000.0, 6000.0, 0.0),
    "DR-DD": TradeUnitRate("DR-DD", "Main Double Door Assembly w/ Heavy Duty Frame & Hardware", "nos", 28000.0, 6000.0, 0.0),
    "DR-FL": TradeUnitRate("DR-FL", "Commercial Flush Door (900x2400) w/ Laminate & Hardware", "nos", 8500.0, 2500.0, 0.0),
    "DR-FD": TradeUnitRate("DR-FD", "Fire Rated Door Assembly (120min) w/ Panic Hardware", "nos", 22000.0, 4500.0, 0.0),
    "DR-UNKNOWN": TradeUnitRate("DR-UNKNOWN", "Standard Commercial Door Assembly", "nos", 9000.0, 2500.0, 0.0),
    # AV & Display
    "AV-01": TradeUnitRate("AV-01", "55\" 4K UHD Commercial Presentation Display w/ Swivel Mount", "nos", 48000.0, 4500.0, 0.0) # ₹52500/No
}


@dataclass
class PricedBOQItem:
    """Individual priced line item with cost lineage."""
    item_code: str
    description: str
    category: str
    net_quantity: float
    wastage_percent: float
    gross_quantity: float
    unit: str
    unit_rate_inr: float
    material_cost_inr: float
    labor_cost_inr: float
    total_amount_inr: float


@dataclass
class PricedProjectEstimate:
    """Comprehensive Project Cost Estimate & Budget Report."""
    drawing_id: str
    drawing_number: str
    revision: str
    fitout_grade: str
    items: list[PricedBOQItem]
    trade_subtotals_inr: dict[str, float]
    direct_cost_subtotal_inr: float
    contractor_overhead_profit_inr: float  # 10%
    contingency_inr: float                # 3%
    net_project_cost_inr: float           # Direct + Markups
    gst_tax_inr: float                    # 18% GST
    grand_total_budget_inr: float         # Net + GST
    cost_per_sqm_inr: float               # Budget benchmark metric (₹/m²)
    cost_per_sqft_inr: float = 0.0        # Commercial fitout standard metric (₹/sqft)

    def to_dict(self) -> dict:
        return {
            "drawing_id": self.drawing_id,
            "drawing_number": self.drawing_number,
            "revision": self.revision,
            "fitout_grade": self.fitout_grade,
            "items": [
                {
                    "item_code": it.item_code,
                    "description": it.description,
                    "category": it.category,
                    "net_quantity": round(it.net_quantity, 2),
                    "wastage_percent": round(it.wastage_percent, 3),
                    "gross_quantity": round(it.gross_quantity, 2),
                    "unit": it.unit,
                    "unit_rate_inr": round(it.unit_rate_inr, 2),
                    "material_cost_inr": round(it.material_cost_inr, 2),
                    "labor_cost_inr": round(it.labor_cost_inr, 2),
                    "total_amount_inr": round(it.total_amount_inr, 2)
                }
                for it in self.items
            ],
            "trade_subtotals_inr": {k: round(v, 2) for k, v in self.trade_subtotals_inr.items()},
            "direct_cost_subtotal_inr": round(self.direct_cost_subtotal_inr, 2),
            "contractor_overhead_profit_inr": round(self.contractor_overhead_profit_inr, 2),
            "contingency_inr": round(self.contingency_inr, 2),
            "net_project_cost_inr": round(self.net_project_cost_inr, 2),
            "gst_tax_inr": round(self.gst_tax_inr, 2),
            "grand_total_budget_inr": round(self.grand_total_budget_inr, 2),
            "cost_per_sqm_inr": round(self.cost_per_sqm_inr, 2),
            "cost_per_sqft_inr": round(self.cost_per_sqft_inr, 2)
        }


class CostEstimationEngine:
    """Computes auditable itemized and project-level budgets from TakeoffSummary."""

    @classmethod
    def estimate_project_cost(
        cls,
        takeoff: TakeoffSummary,
        fitout_grade: FitoutGrade = FitoutGrade.STANDARD,
        overhead_profit_percent: float = 0.10,
        contingency_percent: float = 0.03,
        gst_percent: float = 0.18,
        custom_rates: dict[str, float] | None = None
    ) -> PricedProjectEstimate:
        """Calculates priced BOQ, trade distributions, and grand budget totals."""
        custom_rates = custom_rates or {}

        # Grade multiplier
        grade_mult = 1.0
        if fitout_grade == FitoutGrade.ECONOMY:
            grade_mult = 0.75
        elif fitout_grade == FitoutGrade.GRADE_A_LUXURY:
            grade_mult = 1.45

        priced_items: list[PricedBOQItem] = []
        trade_subtotals: dict[str, float] = defaultdict(float)
        direct_cost = 0.0

        totals = takeoff.total_by_item()
        for code, data in totals.items():
            net_q = data.get("net_quantity", data.get("total_quantity", 0.0))
            w_pct = data.get("wastage_percent", 0.0)
            gross_q = data.get("gross_quantity", net_q)
            unit = data.get("unit", "sqm")
            desc = data.get("description", code)

            # Categorize Trade
            category = cls._categorize_trade(code, desc)

            # Determine Unit Rate
            prefix = (code.split("-")[0].upper() + "-") if "-" in code else (code[:2].upper() + "-")
            trade_fallbacks = {
                "DR-": "DR-UNKNOWN",
                "FL-": "FL-RAW",
                "CL-": "CL-RAW",
                "PT-": "PT-RAW",
                "FN-": "FN-01",
                "MW-": "MW-03",
                "LT-": "LT-03",
                "AV-": "AV-01",
                "SK-": "SK-01",
                "GL-": "GL-01",
            }

            if code in custom_rates:
                unit_rate = float(custom_rates[code])
                mat_rate = unit_rate * 0.70
                lab_rate = unit_rate * 0.30
            elif code in BASELINE_RATES:
                base = BASELINE_RATES[code]
                mat_rate = base.material_rate_inr * grade_mult
                lab_rate = (base.labor_rate_inr + base.machinery_rate_inr) * grade_mult
                unit_rate = mat_rate + lab_rate
            elif prefix in trade_fallbacks and trade_fallbacks[prefix] in BASELINE_RATES:
                base = BASELINE_RATES[trade_fallbacks[prefix]]
                mat_rate = base.material_rate_inr * grade_mult
                lab_rate = (base.labor_rate_inr + base.machinery_rate_inr) * grade_mult
                unit_rate = mat_rate + lab_rate
            else:
                # Default generic fallback
                mat_rate = 1000.0 * grade_mult
                lab_rate = 300.0 * grade_mult
                unit_rate = mat_rate + lab_rate

            # IS 1200 Costing Principle: Material cost applies to Gross Procurement Qty,
            # Labor installation cost applies to Net Measured Qty
            mat_cost = gross_q * mat_rate
            lab_cost = net_q * lab_rate
            item_total = mat_cost + lab_cost

            priced_items.append(PricedBOQItem(
                item_code=code,
                description=desc,
                category=category,
                net_quantity=net_q,
                wastage_percent=w_pct,
                gross_quantity=gross_q,
                unit=unit,
                unit_rate_inr=unit_rate,
                material_cost_inr=mat_cost,
                labor_cost_inr=lab_cost,
                total_amount_inr=item_total
            ))

            trade_subtotals[category] += item_total
            direct_cost += item_total

        # Markups
        oh_profit = direct_cost * overhead_profit_percent
        contingency = direct_cost * contingency_percent
        net_project_cost = direct_cost + oh_profit + contingency
        gst_amount = net_project_cost * gst_percent
        grand_total = net_project_cost + gst_amount

        # Benchmark Cost per Sqm and Sqft
        floor_area = takeoff.base_measurements.get("total_floor_area_sqm") or 0.0
        if not floor_area or float(floor_area) <= 1.0:
            fl_sum = sum(
                it.quantity for it in takeoff.items
                if it.item_code.startswith("FL-") and getattr(it.unit, "value", str(it.unit)).lower() in ("sqm", "m2")
            )
            floor_area = fl_sum if fl_sum > 0 else 1.0

        cost_per_sqm = grand_total / max(1.0, float(floor_area))
        cost_per_sqft = cost_per_sqm / 10.7639104

        return PricedProjectEstimate(
            drawing_id=takeoff.drawing_id,
            drawing_number=takeoff.drawing_number,
            revision=takeoff.revision,
            fitout_grade=fitout_grade.value,
            items=priced_items,
            trade_subtotals_inr=dict(trade_subtotals),
            direct_cost_subtotal_inr=direct_cost,
            contractor_overhead_profit_inr=oh_profit,
            contingency_inr=contingency,
            net_project_cost_inr=net_project_cost,
            gst_tax_inr=gst_amount,
            grand_total_budget_inr=grand_total,
            cost_per_sqm_inr=cost_per_sqm,
            cost_per_sqft_inr=cost_per_sqft
        )

    @staticmethod
    def _categorize_trade(code: str, description: str) -> str:
        c = code.upper()
        d = description.upper()

        # 1. Strict Trade Code Prefix Priority (IS 1200 / Standard Trade Packages)
        if c.startswith("CL-"):
            return "Ceiling & Soffits"
        elif c.startswith("FL-"):
            return "Flooring & Tiling"
        elif c.startswith("GL-"):
            return "Glazing & Acoustic Partitions"
        elif c.startswith("PT-"):
            return "Partitions & Drywalls"
        elif c.startswith("SK-"):
            return "Skirting & Trims"
        elif c.startswith("MW-"):
            return "Joinery & Millwork"
        elif c.startswith("FN-"):
            return "Modular Furniture"
        elif c.startswith("DR-"):
            return "Doors & Ironmongery"
        elif c.startswith("AV-"):
            return "AV & IT Infrastructure"
        elif c.startswith("AC-"):
            return "HVAC & Air Conditioning"
        elif c.startswith("FF-"):
            return "Fire Fighting & Life Safety"
        elif c.startswith("PL-"):
            return "Plumbing & Sanitary"
        elif c.startswith("LT-"):
            return "Electrical & Lighting"

        # 2. Semantic Keyword Matching Fallback
        if "CEILING" in d or "SOFFIT" in d:
            return "Ceiling & Soffits"
        elif "GLASS PARTITION" in d or "GLAZING" in d or "TOUGHENED GLASS" in d:
            return "Glazing & Acoustic Partitions"
        elif "PARTITION" in d or "DRYWALL" in d or "GYPSUM BOARD" in d:
            return "Partitions & Drywalls"
        elif "FLOOR" in d or "CARPET" in d or "VINYL" in d or ("TILE" in d and "WALL" not in d):
            return "Flooring & Tiling"
        elif "SKIRTING" in d:
            return "Skirting & Trims"
        elif "STORAGE" in d or "F.H.S" in d or "O.H.S" in d or "MILLWORK" in d or "JOINERY" in d or "PLANTER" in d or "LEDGE" in d or "CONSOLE" in d or "COUNTER" in d:
            return "Joinery & Millwork"
        elif "WORKSTATION" in d or "SEATING" in d or "CHAIR" in d or "DESK" in d or "TABLE" in d:
            return "Modular Furniture"
        elif "DOOR" in d or "SHUTTER" in d:
            return "Doors & Ironmongery"
        elif "DISPLAY" in d or "TV" in d or "PRESENTATION" in d or "MONITOR" in d or "AUDIO" in d:
            return "AV & IT Infrastructure"
        elif "HVAC" in d or "DIFFUSER" in d or "GRILLE" in d or "AIRCON" in d or "FCU" in d:
            return "HVAC & Air Conditioning"
        elif "SPRINKLER" in d or "FIRE" in d or "SMOKE" in d:
            return "Fire Fighting & Life Safety"
        elif "PLUMBING" in d or "SINK" in d or "FAUCET" in d or "SANITARY" in d or "WASH BASIN" in d:
            return "Plumbing & Sanitary"
        elif "LIGHT" in d or "ELECTRICAL" in d or "FIXTURE" in d or "SWITCH" in d:
            return "Electrical & Lighting"

        return "General Scope"
