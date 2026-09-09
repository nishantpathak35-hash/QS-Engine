"""
QS Quantification Engine — Rule Engine & Takeoff Generator
Executes deterministic QS rules driven purely by YAML profile configurations.
Enforces Blueprint Section 23, Section 24, Section 37 (Lineage & Audit), and Section 80 (Status Model).
Consumes semantic entities and registered calculation functions only.
Enforces strict schema validation, type safety, conflict detection, and status propagation.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any
import yaml

from core.units import DisplayUnit
from core.models.semantics import Room, Opening, OpeningType, WallSegment, BlockInstance, EntityStatus
from core.models.takeoff import TakeoffLineItem, TakeoffSummary
from core.models.project_profile import ProjectProfile
from core.dependency_graph import propagate_dependency_status
from qs.calculator_registry import CalculatorRegistry, UnknownCalculatorError
from qs.rule_schema import RuleProfileSchema, RuleValidationError, MatchPolicy


class QSRuleEngine:
    """Executes deterministic measurement formulas against the semantic drawing model."""

    def __init__(self, profile_path: str | Path | None = None):
        if profile_path is None:
            profile_path = Path(__file__).parent / "profiles" / "standard_interior.yaml"
        self.profile_path = Path(profile_path)
        self.profile = self._load_profile()
        self.rules = self.profile.get("rules", [])
        self.rules_by_code = {r["item_code"]: r for r in self.rules}
        self.rules_by_id = {(r.get("id") or r.get("rule_id")): r for r in self.rules if (r.get("id") or r.get("rule_id"))}

    def _load_profile(self) -> dict:
        if not self.profile_path.exists():
            raise FileNotFoundError(f"QS Profile not found: {self.profile_path}")
        with open(self.profile_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        # Validate loaded profile through strict Pydantic schema
        RuleProfileSchema.validate_raw_profile(raw)
        return raw

    def calculate_takeoff(
        self,
        drawing_id: str,
        drawing_number: str,
        revision: str,
        rooms: list[Room],
        openings: list[Opening] | None = None,
        blocks: list[BlockInstance] | None = None,
        walls: list[WallSegment] | None = None,
        exceptions: list[dict] | None = None,
        assumptions: list[str] | None = None,
        project_profile: ProjectProfile | None = None
    ) -> TakeoffSummary:
        """Applies configured QS measurement rules generically across all drawing entities."""
        openings = openings or []
        blocks = blocks or []
        walls = walls or []
        line_items: list[TakeoffLineItem] = []
        item_counter = 1
        assumptions = list(assumptions or [])
        collected_exceptions = list(exceptions or [])

        # Zero silent fallback: API / engine never runs with uncontrolled defaults
        if project_profile is None:
            project_profile = ProjectProfile.create_strict_default()

        # Dynamically load specified active rule profile if provided
        active_profile_dict = self.profile
        if project_profile and project_profile.active_rule_profile:
            p_name = project_profile.active_rule_profile
            if not p_name.endswith(".yaml") and not p_name.endswith(".yml"):
                p_name = f"{p_name}.yaml"
            candidate = self.profile_path.parent / p_name
            if candidate.exists():
                with open(candidate, "r", encoding="utf-8") as f:
                    candidate_raw = yaml.safe_load(f)
                RuleProfileSchema.validate_raw_profile(candidate_raw)
                active_profile_dict = candidate_raw

        rules = active_profile_dict.get("rules", [])
        rules_by_code = {r["item_code"]: r for r in rules}
        rules_by_id = {(r.get("id") or r.get("rule_id")): r for r in rules if (r.get("id") or r.get("rule_id"))}
        mat_map = active_profile_dict.get("material_mapping", {})
        ceil_map = active_profile_dict.get("ceiling_mapping", {})
        finish_code_map = mat_map.get("finish_codes", {})
        profile_room_mat_map = mat_map.get("room_types", {})
        profile_ceil_map = ceil_map.get("room_types", {})
        profile_version = str(active_profile_dict.get("version", "1.0.0"))

        # Step 0: Compute Base Measurements (Requirement 16)
        total_fl_sqm = sum(r.net_area_sqm for r in rooms)
        total_rm_perim_m = sum(r.perimeter_m for r in rooms)
        total_w_len_m = sum(w.length_m for w in walls)
        base_measurements = {
            "total_room_count": len(rooms),
            "total_floor_area_sqm": round(total_fl_sqm, 2),
            "total_floor_area_sqft": round(total_fl_sqm * 10.7639104, 2),
            "total_room_perimeter_m": round(total_rm_perim_m, 2),
            "total_room_perimeter_rft": round(total_rm_perim_m * 3.28084, 2),
            "total_wall_count": len(walls),
            "total_wall_length_m": round(total_w_len_m, 2),
            "total_wall_length_rft": round(total_w_len_m * 3.28084, 2),
            "total_door_count": sum(1 for op in openings if op.opening_type == OpeningType.DOOR),
            "total_window_count": sum(1 for op in openings if op.opening_type == OpeningType.WINDOW)
        }

        # Step 1: Pre-resolve material evidence per room
        room_finishes: dict[str, dict[str, str | None]] = {}
        rooms_with_matched_flooring: set[str] = set()
        rooms_with_matched_skirting: set[str] = set()
        rooms_with_matched_ceiling: set[str] = set()
        walls_with_matched_partition: set[str] = set()

        for room in rooms:
            fl_code = None
            sk_code = None
            cl_code = None

            # Flooring resolution
            if room.finish_code:
                if room.finish_code in finish_code_map:
                    fl_code = finish_code_map[room.finish_code]
                elif room.finish_code in rules_by_code:
                    fl_code = room.finish_code

            if not fl_code and project_profile.room_finish_mapping_enabled:
                r_upper = room.name.upper()
                for k, code in project_profile.room_finish_mapping.items():
                    if k.upper() in r_upper:
                        fl_code = code
                        break

            if not fl_code and project_profile.allow_assumptions:
                r_upper = room.name.upper()
                for keyword, code in profile_room_mat_map.items():
                    if keyword in r_upper:
                        fl_code = code
                        break

            # Skirting resolution — STRICT: NO MATERIAL FABRICATION FROM FLOORING (Requirement 1)
            if room.skirting_finish_code:
                sk_code = room.skirting_finish_code
            elif project_profile.room_finish_mapping_enabled and project_profile.skirting_finish_mapping:
                r_upper = room.name.upper()
                for k, code in project_profile.skirting_finish_mapping.items():
                    if k.upper() in r_upper:
                        sk_code = code
                        break
            # If no explicit skirting finish code or project approved mapping, sk_code remains None.

            # Ceiling resolution
            if room.ceiling_finish_code:
                cl_code = room.ceiling_finish_code
            elif project_profile.room_finish_mapping_enabled and project_profile.ceiling_finish_mapping:
                r_upper = room.name.upper()
                for k, code in project_profile.ceiling_finish_mapping.items():
                    if k.upper() in r_upper:
                        cl_code = code
                        break
            elif project_profile.allow_assumptions:
                r_upper = room.name.upper()
                for keyword, code in profile_ceil_map.items():
                    if keyword in r_upper:
                        cl_code = code
                        break

            room_finishes[room.id] = {
                "flooring": fl_code,
                "skirting": sk_code,
                "ceiling": cl_code
            }

        # Track exclusive rule matches per entity to detect conflicts (Requirement 14 & 15)
        # entity_id -> category/trade -> list of matched rule_ids
        entity_exclusive_matches: dict[str, dict[str, list[str]]] = {}

        def check_and_record_conflict(entity_id: str, category: str, rule_id: str, is_exclusive: bool) -> bool:
            """Returns True if conflicted and should NOT produce quantity."""
            if not is_exclusive:
                return False
            if entity_id not in entity_exclusive_matches:
                entity_exclusive_matches[entity_id] = {}
            cat_matches = entity_exclusive_matches[entity_id].setdefault(category, [])
            if cat_matches:
                candidate_ids = cat_matches + [rule_id]
                collected_exceptions.append({
                    "code": "AMBIGUOUS_RULE_MATCH",
                    "entity_id": entity_id,
                    "candidate_rules": candidate_ids,
                    "message": f"Entity '{entity_id}' matches multiple mutually exclusive rules: {candidate_ids}",
                    "severity": "ERROR"
                })
                return True
            cat_matches.append(rule_id)
            return False

        # Step 2: Generic Rule Execution Loop
        for rule in rules:
            rule_id = rule.get("id") or rule.get("rule_id") or "UNKNOWN_RULE"
            target = rule.get("target") or rule.get("source_entity")
            applies_when = rule.get("applies_when", {})
            calc_name = rule.get("calculator")
            is_exclusive = (rule.get("match_policy", "exclusive") == "exclusive")
            rule_category = rule.get("category", "general")

            # Validate calculator existence (Requirement 4: NO SILENT FALLBACK)
            if not calc_name or not CalculatorRegistry.is_registered(calc_name):
                collected_exceptions.append({
                    "code": "UNKNOWN_CALCULATOR",
                    "rule_id": rule_id,
                    "calculator": calc_name,
                    "message": f"Rule '{rule_id}' references unknown calculator '{calc_name}'. Rule execution blocked.",
                    "severity": "ERROR"
                })
                continue

            calc_fn = CalculatorRegistry.get(calc_name)

            unit_val = rule.get("unit", "sqm").lower()
            display_unit = (
                DisplayUnit.SQM if unit_val in ("sqm", "m2") else
                DisplayUnit.M if unit_val in ("m", "rm", "lm") else
                DisplayUnit.NOS if unit_val in ("nos", "no", "nr") else
                DisplayUnit.SQM
            )

            # -------------------------------------------------------------
            # Target: Room
            # -------------------------------------------------------------
            if target == "room":
                for room in rooms:
                    fin = room_finishes[room.id]
                    matched = True

                    # Evaluate applicability conditions
                    if "finish_code" in applies_when:
                        req_fl = applies_when["finish_code"]
                        allowed = [req_fl] if isinstance(req_fl, str) else req_fl
                        if fin["flooring"] not in allowed:
                            matched = False
                    elif rule_category in ("flooring", "finishes") and display_unit == DisplayUnit.SQM:
                        if rule.get("item_code") != fin["flooring"]:
                            matched = False

                    if "skirting_finish_code" in applies_when:
                        req_sk = applies_when["skirting_finish_code"]
                        allowed = [req_sk] if isinstance(req_sk, str) else req_sk
                        if fin["skirting"] not in allowed:
                            matched = False
                    elif rule_category == "skirting" or "skirting" in rule.get("id", "").lower() or display_unit == DisplayUnit.M:
                        # Skirting rule without explicit applies_when requires fin["skirting"] == item_code
                        if not fin["skirting"] or rule.get("item_code") != fin["skirting"]:
                            matched = False

                    if "ceiling_finish_code" in applies_when:
                        req_cl = applies_when["ceiling_finish_code"]
                        allowed = [req_cl] if isinstance(req_cl, str) else req_cl
                        if fin["ceiling"] not in allowed:
                            matched = False
                    elif rule_category == "ceiling":
                        if rule.get("item_code") != fin["ceiling"]:
                            matched = False

                    if not matched:
                        continue

                    trade = rule_category
                    if trade in ("finishes", "finish", "general"):
                        if display_unit == DisplayUnit.SQM:
                            trade = "flooring"
                        elif display_unit == DisplayUnit.M or "skirt" in rule.get("id", "").lower() or "skirt" in rule.get("item_code", "").lower():
                            trade = "skirting"
                        elif display_unit == DisplayUnit.NOS:
                            trade = "openings"

                    # Check exclusive conflicts (Requirement 14 & 15)
                    if check_and_record_conflict(room.id, trade, rule_id, is_exclusive):
                        continue

                    # Execute registered calculator
                    calc_res = calc_fn(room=room, openings=openings, rule_config=rule)
                    has_missing_dim = calc_res.get("missing_dimensions", False)
                    
                    # Dependency status propagation (Requirement 7)
                    prereq_statuses = [room.status]
                    if rule_category == "skirting":
                        # Skirting depends on door dimensions
                        source_doors = [op for op in openings if op.id in calc_res.get("source_doors", [])]
                        for d in source_doors:
                            prereq_statuses.append(d.status)
                            if d.is_provisional or d.width_source == "PROJECT_ASSUMPTION":
                                has_missing_dim = True

                    item_status = propagate_dependency_status(
                        base_status=EntityStatus.REVIEW_REQUIRED if (has_missing_dim or room.has_uncertain_boundary) else room.status,
                        prerequisite_statuses=prereq_statuses,
                        has_provisional_inputs=has_missing_dim
                    )

                    # Track trade matching
                    if rule_category in ("flooring", "finishes") and display_unit == DisplayUnit.SQM:
                        rooms_with_matched_flooring.add(room.id)
                    elif rule_category == "skirting" or "skirting" in rule.get("id", "").lower() or display_unit == DisplayUnit.M:
                        rooms_with_matched_skirting.add(room.id)
                    elif rule_category == "ceiling" or "ceiling" in rule.get("id", "").lower():
                        rooms_with_matched_ceiling.add(room.id)

                    item = TakeoffLineItem(
                        id=f"TO-{item_counter:04d}",
                        item_code=rule["item_code"],
                        description=f"{rule.get('description', rule['item_code'])} in {room.name}",
                        location=room.name,
                        quantity=round(calc_res["quantity"], rule.get("rounding", 2)),
                        unit=display_unit,
                        formula=calc_res.get("formula", str(calc_res["quantity"])),
                        source_entities=[room.id] + calc_res.get("source_doors", []),
                        confidence=room.confidence * (0.80 if has_missing_dim or room.has_uncertain_boundary else 1.0),
                        status=item_status,
                        rule_id=rule_id,
                        rule_version=profile_version,
                        calculator=calc_name,
                        measurement_method=rule.get("standard", "IS 1200"),
                        deductions=calc_res.get("deductions", []),
                        assumptions=list(assumptions)
                    )
                    line_items.append(item)
                    item_counter += 1

            # -------------------------------------------------------------
            # Target: Opening / Door / Window
            # -------------------------------------------------------------
            elif target in ("opening", "door", "openings", "window"):
                matched_openings = []
                for op in openings:
                    # Strict subtype applicability (Requirement 2)
                    if applies_when.get("opening_type") and op.opening_type.value != applies_when["opening_type"]:
                        continue
                    if applies_when.get("door_type") and op.door_type != applies_when["door_type"]:
                        continue
                    if applies_when.get("material") and op.material != applies_when["material"]:
                        continue
                    
                    if check_and_record_conflict(op.id, rule_category, rule_id, is_exclusive):
                        continue

                    matched_openings.append(op)

                if matched_openings:
                    calc_res = calc_fn(entities=matched_openings, rule_config=rule)
                    has_provisional = any(
                        op.is_provisional or op.width_m is None or op.width_source == "PROJECT_ASSUMPTION"
                        for op in matched_openings
                    )
                    op_status = propagate_dependency_status(
                        base_status=EntityStatus.AUTO_MEASURED,
                        prerequisite_statuses=[op.status for op in matched_openings],
                        has_provisional_inputs=has_provisional
                    )

                    item = TakeoffLineItem(
                        id=f"TO-{item_counter:04d}",
                        item_code=rule["item_code"],
                        description=rule.get("description", "Openings Count"),
                        location="Project Level",
                        quantity=calc_res["quantity"],
                        unit=display_unit,
                        formula=calc_res.get("formula", f"{len(matched_openings)} Nos"),
                        source_entities=[op.id for op in matched_openings],
                        confidence=min(op.confidence for op in matched_openings),
                        status=op_status,
                        rule_id=rule_id,
                        rule_version=profile_version,
                        calculator=calc_name,
                        measurement_method=rule.get("standard", "IS 1200 Part 8"),
                        deductions=calc_res.get("deductions", []),
                        assumptions=list(assumptions)
                    )
                    line_items.append(item)
                    item_counter += 1

            # -------------------------------------------------------------
            # Target: Wall / Partition (Requirement 3)
            # -------------------------------------------------------------
            elif target in ("wall", "walls", "partition"):
                for w in walls:
                    matched = True
                    if applies_when.get("wall_type") and w.wall_type != applies_when["wall_type"]:
                        matched = False
                    if applies_when.get("partition_type") and w.partition_type != applies_when["partition_type"]:
                        matched = False
                    if applies_when.get("classification") and w.classification != applies_when["classification"]:
                        matched = False

                    if not matched:
                        continue

                    if check_and_record_conflict(w.id, rule_category, rule_id, is_exclusive):
                        continue

                    # Wall height resolution & assumption tracking (Requirement 6 & 7)
                    effective_height = w.height_m
                    is_height_assumed = False
                    if effective_height is None:
                        if project_profile and project_profile.is_assumption_approved("default_ceiling_height_m"):
                            effective_height = project_profile.get_approved_dimension("default_ceiling_height_m")
                            is_height_assumed = True
                            assumptions.append(f"Wall '{w.id}' height assumed as {effective_height:.2f}m from project profile")
                        elif project_profile and project_profile.allow_assumptions and project_profile.ceiling_height_m:
                            effective_height = project_profile.ceiling_height_m
                            is_height_assumed = True
                            assumptions.append(f"Wall '{w.id}' height assumed as {effective_height:.2f}m from project profile ceiling height")
                        else:
                            collected_exceptions.append({
                                "code": "MISSING_WALL_HEIGHT",
                                "wall_id": w.id,
                                "layer": w.layer,
                                "message": f"Wall segment '{w.id}' has missing height. Partition quantity requires height.",
                                "severity": "WARNING"
                            })

                    # Execute calculator (e.g. wall.partition_area or generic.linear_length)
                    cfg = dict(rule)
                    if effective_height is not None:
                        cfg["wall_height_m"] = effective_height

                    calc_res = calc_fn(wall=w, openings=openings, rule_config=cfg)
                    has_missing = calc_res.get("missing_height", False) or (effective_height is None) or is_height_assumed or calc_res.get("missing_dimensions", False)

                    wall_item_status = propagate_dependency_status(
                        base_status=EntityStatus.REVIEW_REQUIRED if has_missing else w.status,
                        prerequisite_statuses=[w.status],
                        has_provisional_inputs=has_missing
                    )

                    walls_with_matched_partition.add(w.id)

                    item = TakeoffLineItem(
                        id=f"TO-{item_counter:04d}",
                        item_code=rule["item_code"],
                        description=f"{rule.get('description', 'Partition')} ({w.id})",
                        location=f"Wall {w.id}",
                        quantity=round(calc_res["quantity"], rule.get("rounding", 2)),
                        unit=display_unit,
                        formula=calc_res.get("formula", f"Wall length {w.length_m:.2f}m"),
                        source_entities=[w.id] + calc_res.get("source_openings", []),
                        confidence=w.confidence * (0.80 if has_missing else 1.0),
                        status=wall_item_status,
                        rule_id=rule.get("id", "QS-WALL-001"),
                        rule_version=profile_version,
                        calculator=calc_name,
                        measurement_method=rule.get("standard", "IS 1200 Part 4"),
                        deductions=calc_res.get("deductions", []),
                        assumptions=list(assumptions)
                    )
                    line_items.append(item)
                    item_counter += 1

        # Step 3: Handle Unassigned Rooms (Raw Geometry Preservation — Requirements 1 & 16)
        for room in rooms:
            if room.id not in rooms_with_matched_flooring:
                collected_exceptions.append({
                    "code": "UNKNOWN_FLOOR_FINISH",
                    "room_id": room.id,
                    "location": room.name,
                    "message": f"Room '{room.name}' has measured area of {room.net_area_sqm:.2f} sqm but no floor finish code or profile mapping.",
                    "severity": "WARNING"
                })
                line_items.append(TakeoffLineItem(
                    id=f"TO-{item_counter:04d}",
                    item_code="FL-RAW",
                    description=f"Measured Floor Area in {room.name} (Unassigned Finish)",
                    location=room.name,
                    quantity=room.net_area_sqm,
                    unit=DisplayUnit.SQM,
                    formula=f"Room polygon area = {room.net_area_sqm:.3f} sqm",
                    source_entities=[room.id],
                    confidence=min(room.confidence, 0.70),
                    status=EntityStatus.RAW_MEASURED,
                    rule_id="QS-FL-UNASSIGNED",
                    rule_version=profile_version,
                    calculator="generic.polygon_net_area",
                    measurement_method=f"{self.profile.get('standard', 'IS 1200')} (Geometry Boundary Area)",
                    deductions=[],
                    assumptions=list(assumptions)
                ))
                item_counter += 1

            if room.id not in rooms_with_matched_ceiling:
                collected_exceptions.append({
                    "code": "UNKNOWN_CEILING_FINISH",
                    "room_id": room.id,
                    "location": room.name,
                    "message": f"Room '{room.name}' has measured ceiling area of {room.gross_area_sqm:.2f} sqm but no ceiling finish mapping.",
                    "severity": "WARNING"
                })
                line_items.append(TakeoffLineItem(
                    id=f"TO-{item_counter:04d}",
                    item_code="CL-RAW",
                    description=f"Measured Ceiling Area in {room.name} (Unassigned Finish)",
                    location=room.name,
                    quantity=room.gross_area_sqm,
                    unit=DisplayUnit.SQM,
                    formula=f"Ceiling area = {room.gross_area_sqm:.3f} sqm",
                    source_entities=[room.id],
                    confidence=min(room.confidence, 0.70),
                    status=EntityStatus.RAW_MEASURED,
                    rule_id="QS-CL-UNASSIGNED",
                    rule_version=profile_version,
                    calculator="generic.polygon_gross_area",
                    measurement_method=f"{self.profile.get('standard', 'IS 1200')} (Geometry Boundary Area)",
                    deductions=[],
                    assumptions=list(assumptions)
                ))
                item_counter += 1

            if room.id not in rooms_with_matched_skirting:
                collected_exceptions.append({
                    "code": "UNKNOWN_SKIRTING_FINISH",
                    "room_id": room.id,
                    "location": room.name,
                    "message": f"Room '{room.name}' has measured perimeter of {room.perimeter_m:.2f} m but no skirting finish mapping.",
                    "severity": "WARNING"
                })


        # Step 4: Handle Unassigned Doors (Requirement 2)
        door_openings = [op for op in openings if op.opening_type == OpeningType.DOOR]
        accounted_door_ids = set()
        for item in line_items:
            if "DR" in item.item_code or "door" in item.description.lower():
                accounted_door_ids.update(item.source_entities)

        unaccounted_doors = [d for d in door_openings if d.id not in accounted_door_ids]
        if unaccounted_doors:
            collected_exceptions.append({
                "code": "UNKNOWN_DOOR_SUBTYPE",
                "message": f"{len(unaccounted_doors)} door openings have unknown door subtype. Review required.",
                "severity": "WARNING"
            })
            line_items.append(TakeoffLineItem(
                id=f"TO-{item_counter:04d}",
                item_code="DR-UNKNOWN",
                description="Unclassified Door Openings (Review Required)",
                location="Project Level",
                quantity=float(len(unaccounted_doors)),
                unit=DisplayUnit.NOS,
                formula=f"Count of unclassified doors = {len(unaccounted_doors)} Nos",
                source_entities=[d.id for d in unaccounted_doors],
                confidence=0.60,
                status=EntityStatus.REVIEW_REQUIRED,
                rule_id="QS-DR-UNKNOWN",
                rule_version=profile_version,
                calculator="generic.count",
                measurement_method="Geometry Count",
                deductions=[],
                assumptions=list(assumptions)
            ))
            item_counter += 1

        # Step 5: Handle Unassigned Partition Walls (Requirement 3 & 16)
        partition_walls = [w for w in walls if w.wall_type == "partition" or w.classification == "partition"]
        unmatched_partition_walls = [w for w in partition_walls if w.id not in walls_with_matched_partition]
        if unmatched_partition_walls:
            collected_exceptions.append({
                "code": "UNKNOWN_PARTITION_TYPE",
                "message": f"{len(unmatched_partition_walls)} partition wall segments have unknown partition type.",
                "severity": "WARNING"
            })
            total_unassigned_len = sum(w.length_m for w in unmatched_partition_walls)
            line_items.append(TakeoffLineItem(
                id=f"TO-{item_counter:04d}",
                item_code="PT-RAW",
                description="Unclassified Partition Walls (Centerline Length)",
                location="Project Level",
                quantity=round(total_unassigned_len, 2),
                unit=DisplayUnit.M,
                formula=f"Sum of {len(unmatched_partition_walls)} wall lengths = {total_unassigned_len:.3f} m (Unassigned Type)",
                source_entities=[w.id for w in unmatched_partition_walls],
                confidence=0.70,
                status=EntityStatus.RAW_MEASURED,
                rule_id="QS-PT-UNASSIGNED",
                rule_version=profile_version,
                calculator="generic.linear_length",
                measurement_method="Centerline Linear Measurement",
                deductions=[],
                assumptions=list(assumptions)
            ))
            item_counter += 1

        # Step 6: Assign Procurement Wastage Factors (IS 1200 / POMI Standard)
        if project_profile:
            import math
            for item in line_items:
                w_factor = project_profile.get_wastage_percent(item.item_code, item.description)
                item.wastage_percent = w_factor
                if item.unit == DisplayUnit.NOS and w_factor > 0:
                    item.gross_quantity = float(math.ceil(item.quantity * (1.0 + w_factor)))
                else:
                    item.gross_quantity = round(item.quantity * (1.0 + w_factor), 2)

        return TakeoffSummary(
            drawing_id=drawing_id,
            drawing_number=drawing_number,
            revision=revision,
            items=line_items,
            exceptions=collected_exceptions,
            base_measurements=base_measurements
        )
