"""
QS Quantification Engine — Drawing Schedule & Legend Parser
Extracts tabulated schedules (Lighting, Electrical, FF&E) and workstation capacity tags from drawings.
Supports Blueprint Section 15 (Module 10 — Text & Schedule Mining) with zero marginal AI cost.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from core.models.semantics import EntityStatus
from core.models.takeoff import TakeoffLineItem
from core.units import DisplayUnit
from parsers.dxf.reader import ExtractedText


@dataclass
class ScheduleItem:
    item_code: str
    category: str
    description: str
    quantity: float
    unit: str
    location: str = "Project Level"
    status: EntityStatus = EntityStatus.AUTO_MEASURED


class DrawingScheduleParser:
    """Parses drawing legends, fixture schedules, and capacity annotations."""

    @staticmethod
    def extract_schedule_items(texts: list[ExtractedText], drawing_id: str = "") -> list[TakeoffLineItem]:
        """Discovers schedule tables (Lighting, Electrical, FF&E) and capacity tags."""
        items: list[TakeoffLineItem] = []
        if not texts:
            return items

        # 1. Legend Table Extraction (e.g. LIGHTING LEGEND, FIXTURE SCHEDULE)
        legend_items = DrawingScheduleParser._parse_legend_tables(texts, drawing_id)
        items.extend(legend_items)

        # 2. Workstation & Seating Capacity Extraction (e.g. 38 PAX WORKSTATIONS)
        workstation_items = DrawingScheduleParser._parse_workstation_capacities(texts, drawing_id)
        items.extend(workstation_items)

        return items

    @staticmethod
    def _parse_legend_tables(texts: list[ExtractedText], drawing_id: str) -> list[TakeoffLineItem]:
        items: list[TakeoffLineItem] = []

        # Find header tokens: QTY, QUANTITY, NOS
        qty_headers = [
            t for t in texts
            if t.content.strip().upper() in ("QTY", "QUANTITY", "NOS", "COUNT")
        ]

        for q_hdr in qty_headers:
            # Find quantity values in the same vertical column (|x - q_hdr.x| < 400mm and y < q_hdr.y)
            col_x = q_hdr.location.x
            col_y = q_hdr.location.y

            qty_tokens = [
                t for t in texts
                if abs(t.location.x - col_x) < 400.0
                and t.location.y < (col_y - 50.0)
                and abs(t.location.y - col_y) < 6000.0
                and t.content.strip().isdigit()
            ]
            qty_tokens.sort(key=lambda t: -t.location.y)

            item_counter = 1
            for q_tok in qty_tokens:
                qty_val = float(q_tok.content.strip())
                if qty_val <= 0:
                    continue

                # Find description text to the left of the quantity column (|y - q_tok.y| < 260mm, x < col_x - 500mm)
                row_y = q_tok.location.y
                row_texts = [
                    t for t in texts
                    if (col_x - 4500.0) < t.location.x < (col_x - 600.0)
                    and abs(t.location.y - row_y) < 260.0
                ]

                if not row_texts:
                    continue

                desc = DrawingScheduleParser._reconstruct_cell_text(row_texts)
                if not desc or len(desc) < 2:
                    continue

                # Clean up description
                desc = DrawingScheduleParser._clean_lighting_description(desc)
                d_upper = desc.upper()

                # Dynamic Trade Prefix & Location Resolution
                if any(k in d_upper for k in ("DOOR", "FLUSH DOOR", "FRAME", "SHUTTER", "PANIC")):
                    prefix = "DR"
                    loc = "Door & Opening Schedule"
                elif any(k in d_upper for k in ("WORKSTATION", "CHAIR", "DESK", "TABLE", "SEATING", "SOFA", "OTTOMAN")):
                    prefix = "FN"
                    loc = "Furniture Schedule"
                elif any(k in d_upper for k in ("STORAGE", "CABINET", "MILLWORK", "JOINERY", "WARDROBE", "PLANTER", "F.H.S", "O.H.S", "CONSOLE")):
                    prefix = "MW"
                    loc = "Millwork Schedule"
                elif any(k in d_upper for k in ("DIFFUSER", "GRILLE", "HVAC", "CASSETTE", "DUCT", "FCU", "VRV", "VRF")):
                    prefix = "AC"
                    loc = "HVAC & Mechanical Schedule"
                elif any(k in d_upper for k in ("SPRINKLER", "SMOKE", "DETECTOR", "FIRE", "EXTINGUISHER")):
                    prefix = "FF"
                    loc = "Fire Protection Schedule"
                elif any(k in d_upper for k in ("LIGHT", "LED", "LAMP", "DOWNLIGHT", "PENDANT", "FIXTURE", "LUMINAIRE")):
                    prefix = "LT"
                    loc = "Lighting Legend Schedule"
                else:
                    prefix = "EQ"
                    loc = "Fixture & Equipment Schedule"

                item_code = f"{prefix}-{item_counter:02d}"
                items.append(TakeoffLineItem(
                    id=f"TO-SCH-{item_code}",
                    item_code=item_code,
                    description=desc,
                    location=loc,
                    quantity=qty_val,
                    unit=DisplayUnit.NOS,
                    formula=f"Extracted from Drawing Legend (Qty = {int(qty_val)} Nos)",
                    confidence=0.98,
                    status=EntityStatus.AUTO_MEASURED,
                    source_entities=[f"LEGEND-ROW-{item_counter}"]
                ))
                item_counter += 1

        return items

    @staticmethod
    def _parse_workstation_capacities(texts: list[ExtractedText], drawing_id: str) -> list[TakeoffLineItem]:
        items: list[TakeoffLineItem] = []

        # Find PAX tokens
        pax_tokens = [t for t in texts if "PAX" in t.content.upper()]

        total_workstations = 0
        total_conference_seats = 0
        ws_sources = []
        conf_sources = []

        for p_tok in pax_tokens:
            # Look for number immediately adjacent (|x - p_tok.x| < 1200mm, |y - p_tok.y| < 300mm)
            nearby = [
                t for t in texts
                if abs(t.location.x - p_tok.location.x) < 1400.0
                and abs(t.location.y - p_tok.location.y) < 300.0
                and t != p_tok
            ]

            num_val = None
            for nb in nearby:
                cleaned = nb.content.strip()
                if cleaned.isdigit():
                    num_val = int(cleaned)
                    break
                # Handle combined like "38 PAX"
                m = re.search(r"\b(\d+)\s*PAX\b", p_tok.content.upper())
                if m:
                    num_val = int(m.group(1))
                    break

            if num_val and num_val > 0:
                # Check surrounding area (|dx| < 2500, |dy| < 1500) for context (WORKSTATIONS vs CONFERENCE)
                context_texts = [
                    t.content.upper() for t in texts
                    if abs(t.location.x - p_tok.location.x) < 2500.0
                    and abs(t.location.y - p_tok.location.y) < 1500.0
                ]
                context_str = " ".join(context_texts)

                if "CONFERENCE" in context_str or "BOARDROOM" in context_str or "MEETING" in context_str:
                    total_conference_seats += num_val
                    conf_sources.append(f"{num_val} PAX Conference")
                else:
                    total_workstations += num_val
                    ws_sources.append(f"{num_val} PAX Workstations")

        if total_workstations > 0:
            items.append(TakeoffLineItem(
                id="TO-FN-01",
                item_code="FN-01",
                description=f"Modular Linear / Cluster Workstations ({total_workstations} Seats Capacity)",
                location="Open Office Workspace",
                quantity=float(total_workstations),
                unit=DisplayUnit.NOS,
                formula=f"Sum of Drawing Workstation Tags ({', '.join(ws_sources)})",
                confidence=0.96,
                status=EntityStatus.AUTO_MEASURED,
                source_entities=ws_sources
            ))

        if total_conference_seats > 0:
            items.append(TakeoffLineItem(
                id="TO-FN-02",
                item_code="FN-02",
                description=f"Conference / Meeting Room Executive Seating ({total_conference_seats} Seats)",
                location="Conference Room",
                quantity=float(total_conference_seats),
                unit=DisplayUnit.NOS,
                formula=f"Sum of Conference Seating Tags ({', '.join(conf_sources)})",
                confidence=0.96,
                status=EntityStatus.AUTO_MEASURED,
                source_entities=conf_sources
            ))

        return items

    @staticmethod
    def _reconstruct_cell_text(tokens: list[ExtractedText]) -> str:
        """Reconstructs multiline cell text by clustering horizontal rows and ordering left-to-right."""
        lines: list[list[ExtractedText]] = []
        sorted_tokens = sorted(tokens, key=lambda t: -t.location.y)
        for t in sorted_tokens:
            placed = False
            for l in lines:
                if abs(l[0].location.y - t.location.y) < 40.0:
                    l.append(t)
                    placed = True
                    break
            if not placed:
                lines.append([t])

        line_strs = []
        for line in lines:
            line.sort(key=lambda t: t.location.x)
            s = ""
            last_x = None
            for t in line:
                if last_x is not None and (t.location.x - last_x) > 60.0:
                    s += " "
                s += t.content
                last_x = t.location.x + (getattr(t, "width_mm", 40.0) or 40.0)
            line_strs.append(s.strip())
        return " ".join(line_strs)

    @staticmethod
    def _clean_lighting_description(text: str) -> str:
        """Normalizes broken or spaced words in CAD legend descriptions."""
        # Replace common OCR/exploded patterns
        cleaned = text
        cleaned = re.sub(r"CYLIN\s+DERIC\s+AL\s+HAN\s+GIN\s+G", "CYLINDRICAL HANGING", cleaned)
        cleaned = re.sub(r"DECOR\s+ATIVE", "DECORATIVE", cleaned)
        cleaned = re.sub(r"DIREC\s+TO\s+R\'S", "DIRECTOR'S", cleaned)
        cleaned = re.sub(r"DECO\s+RATI\s+VE", "DECORATIVE", cleaned)
        cleaned = re.sub(r"LI\s+GHT", "LIGHT", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
