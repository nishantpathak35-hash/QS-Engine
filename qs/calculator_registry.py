"""
QS Quantification Engine — Calculator Function Registry
Provides executable calculation dispatch for generic YAML-driven rules.
Enforces Blueprint Section 24 and Section 37 (Lineage & Audit).
Enforces Calculator Type Safety and blocks invalid fallbacks.
"""

from __future__ import annotations
from typing import Callable, Any
from core.models.semantics import Room, Opening, OpeningType, WallSegment, EntityStatus
from core.geometry.primitives import Polygon2D
from qs.is1200_rules import IS1200TradeRules


class UnknownCalculatorError(Exception):
    """Raised when a YAML rule references a calculator not present in the registry."""
    pass


class CalculatorRegistry:
    """Registry of executable QS measurement functions referenced by YAML rule profiles."""

    _registry: dict[str, Callable] = {}
    _supported_entities: dict[str, list[str]] = {}

    @classmethod
    def register(cls, name: str, supported_entities: list[str] | None = None):
        """Decorator to register a calculation function with its supported source entities."""
        def decorator(fn: Callable):
            cls._registry[name] = fn
            cls._supported_entities[name] = supported_entities or [
                "room", "wall", "opening", "door", "window", "finish_region", "polyline", "entities"
            ]
            return fn
        return decorator

    @classmethod
    def get(cls, name: str) -> Callable | None:
        """Retrieves a registered calculation function by name."""
        return cls._registry.get(name)

    @classmethod
    def is_registered(cls, name: str) -> bool:
        return name in cls._registry

    @classmethod
    def get_supported_entities(cls, name: str) -> list[str]:
        return cls._supported_entities.get(name, [])

    @classmethod
    def validate_compatibility(cls, name: str, source_entity: str) -> bool:
        """Validates that the source entity type is supported by the calculator."""
        if name not in cls._registry:
            return False
        supported = cls._supported_entities.get(name, [])
        norm_source = source_entity.lower().strip().rstrip("s")
        norm_supported = [s.lower().strip().rstrip("s") for s in supported]
        return norm_source in norm_supported or "entity" in norm_supported or "entitie" in norm_supported


# ---------------------------------------------------------------------------
# Registered Built-in Calculators
# ---------------------------------------------------------------------------

@CalculatorRegistry.register("is1200.flooring_with_door_rebates", supported_entities=["room", "finish_region"])
def calc_is1200_flooring(
    room: Room,
    openings: list[Opening] | None = None,
    rule_config: dict | None = None,
    **kwargs
) -> dict[str, Any]:
    """Calculates net flooring per IS 1200 Part 11."""
    import shapely.geometry as sg

    cutouts = [Polygon2D(hole) for hole in room.polygon.holes]
    door_rebate_added = rule_config.get("door_rebate_added", False) if rule_config else False
    
    room_doors = []
    if door_rebate_added:
        room_shapely = sg.Polygon([(v.x, v.y) for v in room.polygon.vertices])
        for op in (openings or []):
            if op.opening_type == OpeningType.DOOR and op.width_m is not None:
                op_pt = sg.Point(op.location.x, op.location.y)
                dist = room_shapely.boundary.distance(op_pt)
                if dist <= 350.0:
                    room_doors.append(op)

    res = IS1200TradeRules.calculate_flooring_with_door_rebates(
        room.polygon,
        floor_cutouts=cutouts,
        doors=room_doors
    )
    return {
        "quantity": res.net_flooring_area_sqm,
        "formula": res.formula_lineage,
        "deductions": [{"type": "VOID_CUTOUT", "value": res.deducted_voids_sqm, "unit": "sqm"}] if res.deducted_voids_sqm > 0 else []
    }


@CalculatorRegistry.register("is1200.ceiling_with_thresholds", supported_entities=["room"])
def calc_is1200_ceiling(
    room: Room,
    openings: list[Opening] | None = None,
    rule_config: dict | None = None,
    **kwargs
) -> dict[str, Any]:
    """Calculates net ceiling per IS 1200 Part 7."""
    cutouts = [Polygon2D(hole) for hole in room.polygon.holes]
    res = IS1200TradeRules.calculate_ceiling_with_thresholds(room.polygon, ceiling_cutouts=cutouts)
    return {
        "quantity": res.net_ceiling_area_sqm,
        "formula": res.formula_lineage,
        "deductions": [{"type": "OPENING_CUTOUT", "value": res.deducted_openings_sqm, "unit": "sqm"}] if res.deducted_openings_sqm > 0 else []
    }


@CalculatorRegistry.register("is1200.skirting_with_deductions", supported_entities=["room"])
def calc_is1200_skirting(
    room: Room,
    openings: list[Opening] | None = None,
    rule_config: dict | None = None,
    **kwargs
) -> dict[str, Any]:
    """Calculates skirting with boundary door deductions per IS 1200 Part 4/11."""
    import shapely.geometry as sg

    deduct = rule_config.get("deduct_openings", True) if rule_config else True
    gross_perim = room.perimeter_m
    
    if not deduct:
        return {
            "quantity": gross_perim,
            "formula": f"Gross internal perimeter = {gross_perim:.3f} m (no deductions per rule config)",
            "deductions": [],
            "source_doors": [],
            "missing_dimensions": False
        }

    room_shapely = sg.Polygon([(v.x, v.y) for v in room.polygon.vertices])
    door_deductions = []
    source_doors = []
    total_deduction_m = 0.0
    has_missing_dimension = False

    for op in (openings or []):
        if op.opening_type == OpeningType.DOOR:
            op_pt = sg.Point(op.location.x, op.location.y)
            dist = room_shapely.boundary.distance(op_pt)
            if op.jamb_p1 and op.jamb_p2:
                jline = sg.LineString([op.jamb_p1.to_tuple(), op.jamb_p2.to_tuple()])
                dist = min(dist, room_shapely.boundary.distance(jline))

            if dist <= 350.0:
                source_doors.append(op.id)
                if op.width_m is not None:
                    total_deduction_m += op.width_m
                    door_deductions.append({
                        "type": "DOOR_OPENING",
                        "source_entity": op.id,
                        "deduction_value": round(op.width_m, 3),
                        "unit": "m",
                        "reason": "IS 1200 door opening skirting deduction"
                    })
                else:
                    has_missing_dimension = True

    net_perim = max(0.0, gross_perim - total_deduction_m)
    formula_str = (
        f"Perimeter ({gross_perim:.3f}m) - Door deduction ({total_deduction_m:.3f}m) = {net_perim:.3f} m"
    )
    return {
        "quantity": net_perim,
        "formula": formula_str,
        "deductions": door_deductions,
        "source_doors": source_doors,
        "missing_dimensions": has_missing_dimension
    }


@CalculatorRegistry.register("generic.polygon_net_area", supported_entities=["room", "finish_region"])
def calc_generic_net_area(room: Room, **kwargs) -> dict[str, Any]:
    return {
        "quantity": room.net_area_sqm,
        "formula": f"Room polygon net area = {room.net_area_sqm:.3f} sqm",
        "deductions": []
    }


@CalculatorRegistry.register("generic.polygon_gross_area", supported_entities=["room", "finish_region"])
def calc_generic_gross_area(room: Room, **kwargs) -> dict[str, Any]:
    return {
        "quantity": room.gross_area_sqm,
        "formula": f"Room polygon gross area = {room.gross_area_sqm:.3f} sqm",
        "deductions": []
    }


@CalculatorRegistry.register("generic.polygon_area", supported_entities=["room", "finish_region"])
def calc_generic_polygon_area(room: Room, rule_config: dict | None = None, **kwargs) -> dict[str, Any]:
    use_gross = rule_config.get("gross", False) if rule_config else False
    qty = room.gross_area_sqm if use_gross else room.net_area_sqm
    kind = "gross" if use_gross else "net"
    return {
        "quantity": qty,
        "formula": f"Room polygon {kind} area = {qty:.3f} sqm",
        "deductions": []
    }


@CalculatorRegistry.register("generic.perimeter", supported_entities=["room"])
def calc_generic_perimeter(room: Room, **kwargs) -> dict[str, Any]:
    return {
        "quantity": room.perimeter_m,
        "formula": f"Boundary perimeter = {room.perimeter_m:.3f} m",
        "deductions": []
    }


@CalculatorRegistry.register("generic.linear_length", supported_entities=["wall", "polyline", "entities"])
def calc_generic_linear_length(entities: list[Any] | None = None, wall: Any = None, **kwargs) -> dict[str, Any]:
    target_list = entities if entities is not None else ([wall] if wall else [])
    total_len = sum(getattr(e, "length_m", 0.0) for e in target_list)
    return {
        "quantity": total_len,
        "formula": f"Sum of {len(target_list)} segment lengths = {total_len:.3f} m",
        "deductions": []
    }


@CalculatorRegistry.register("generic.count", supported_entities=["opening", "door", "window", "block", "wall", "room", "entities"])
def calc_generic_count(entities: list[Any], rule_config: dict | None = None, **kwargs) -> dict[str, Any]:
    count = float(len(entities))
    return {
        "quantity": count,
        "formula": f"Count of validated entities = {int(count)} Nos",
        "deductions": []
    }


@CalculatorRegistry.register("generic.subtract_openings", supported_entities=["room", "wall"])
def calc_generic_subtract_openings(
    room: Room | None = None,
    wall: WallSegment | None = None,
    openings: list[Opening] | None = None,
    rule_config: dict | None = None,
    **kwargs
) -> dict[str, Any]:
    """Generic operator subtracting opening dimensions from entity measurement."""
    dimension = rule_config.get("dimension", "width") if rule_config else "width"
    if room is not None:
        base_qty = room.perimeter_m if dimension == "width" else room.gross_area_sqm
    elif wall is not None:
        base_qty = wall.length_m
    else:
        base_qty = 0.0

    total_deduct = 0.0
    deductions = []

    for op in (openings or []):
        val = op.width_m if dimension == "width" else op.area_sqm
        if val is not None:
            total_deduct += val
            deductions.append({"entity_id": op.id, "value": val, "dimension": dimension})

    net_qty = max(0.0, base_qty - total_deduct)
    return {
        "quantity": net_qty,
        "formula": f"Base ({base_qty:.3f}) - Deductions ({total_deduct:.3f}) = {net_qty:.3f}",
        "deductions": deductions
    }


@CalculatorRegistry.register("generic.multiply_dimension", supported_entities=["wall", "polyline", "entities"])
def calc_generic_multiply_dimension(
    entities: list[Any] | None = None,
    wall: Any = None,
    rule_config: dict | None = None,
    **kwargs
) -> dict[str, Any]:
    target_list = entities if entities is not None else ([wall] if wall else [])
    multiplier = rule_config.get("multiplier", 1.0) if rule_config else 1.0
    total = sum(getattr(e, "length_m", 1.0) for e in target_list) * multiplier
    return {
        "quantity": total,
        "formula": f"Dimension multiplied by {multiplier} = {total:.3f}",
        "deductions": []
    }


@CalculatorRegistry.register("wall.partition_area", supported_entities=["wall", "polyline"])
def calc_wall_partition_area(
    wall: WallSegment | None = None,
    entities: list[WallSegment] | None = None,
    openings: list[Opening] | None = None,
    rule_config: dict | None = None,
    **kwargs
) -> dict[str, Any]:
    """
    Calculates drywall / partition area per IS 1200 Part 4:
    Gross Area = Length * Height
    Net Area = Gross Area - Opening Deductions
    """
    import shapely.geometry as sg

    target_walls = entities if entities is not None else ([wall] if wall is not None else [])
    default_h = rule_config.get("wall_height_m") or rule_config.get("default_height_m") if rule_config else None
    deduct_openings = rule_config.get("deduct_openings", True) if rule_config else True

    total_gross = 0.0
    total_deductions = 0.0
    deduction_details = []
    source_opening_ids = []
    missing_height = False
    missing_dimensions = False

    for w in target_walls:
        h = w.height_m if w.height_m is not None else default_h
        if h is None:
            missing_height = True
            h = 0.0

        w_gross = w.length_m * h
        total_gross += w_gross

        if deduct_openings and openings:
            w_line = sg.LineString([(w.start.x, w.start.y), (w.end.x, w.end.y)])
            for op in openings:
                is_hosted = (op.host_wall_id == w.id)
                is_proximate = False
                if not is_hosted:
                    op_pt = sg.Point(op.location.x, op.location.y)
                    dist = w_line.distance(op_pt)
                    if dist <= max(w.thickness_mm * 1.5, 300.0):
                        is_proximate = True

                if is_hosted or is_proximate:
                    source_opening_ids.append(op.id)
                    if op.area_sqm is not None:
                        ded_val = op.area_sqm
                        total_deductions += ded_val
                        deduction_details.append({
                            "opening_id": op.id,
                            "type": op.opening_type.value,
                            "area_sqm": round(ded_val, 3)
                        })
                    elif op.width_m is not None and h > 0:
                        # If opening height not specified, assume standard door height 2.1m or wall height
                        op_h = op.height_m or min(2.10, h)
                        ded_val = op.width_m * op_h
                        total_deductions += ded_val
                        deduction_details.append({
                            "opening_id": op.id,
                            "type": op.opening_type.value,
                            "area_sqm": round(ded_val, 3)
                        })
                    else:
                        missing_dimensions = True

    net_area = max(0.0, total_gross - total_deductions)
    formula = (
        f"Length ({sum(w.length_m for w in target_walls):.2f}m) * Height - "
        f"Openings ({total_deductions:.2f} sqm) = {net_area:.2f} sqm"
    )
    return {
        "quantity": net_area,
        "gross_quantity": total_gross,
        "formula": formula,
        "deductions": deduction_details,
        "source_openings": source_opening_ids,
        "missing_height": missing_height,
        "missing_dimensions": missing_dimensions
    }


@CalculatorRegistry.register("is1200.wall_plastering_net_area", supported_entities=["room"])
def calc_is1200_wall_plastering(
    room: Room,
    openings: list[Opening] | None = None,
    rule_config: dict | None = None,
    **kwargs
) -> dict[str, Any]:
    """Calculates internal wall plastering per IS 1200 Part 12 (Perimeter * Height less openings)."""
    h_m = float(rule_config.get("wall_height_m", 2.70)) if rule_config else 2.70
    gross_wall_area = room.perimeter_m * h_m
    total_deductions = 0.0
    deductions = []

    for op in (openings or []):
        if op.area_sqm is not None:
            if op.area_sqm > 0.50:
                ded_val = op.area_sqm if op.area_sqm <= 3.0 else (op.area_sqm * 2.0)
                total_deductions += ded_val
                deductions.append({"opening_id": op.id, "area_sqm": op.area_sqm, "deduction_sqm": ded_val})

    net_area = max(0.0, gross_wall_area - total_deductions)
    return {
        "quantity": net_area,
        "formula": f"Gross wall area ({gross_wall_area:.2f} sqm) - IS1200 opening deductions ({total_deductions:.2f} sqm) = {net_area:.2f} sqm",
        "deductions": deductions
    }
