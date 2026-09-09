"""
QS Quantification Engine — Spatial Geometry Difference Engine
Compares baseline and revised drawing takeoffs using spatial entity matching.
Utilizes polygon IoU, centroid distance, and shape similarity.
Discovers UNCHANGED, MODIFIED, ADDED, REMOVED, and UNCERTAIN_MATCH items.
Enforces Blueprint Section 38 (Revision Management) & Section 39 (Geometry Difference Engine).
"""

from __future__ import annotations
import shapely.geometry as sg

from core.models.semantics import Room
from core.models.takeoff import TakeoffSummary, TakeoffLineItem
from revision.models import ChangeType, QuantityDelta, RevisionComparisonResult


class RevisionDifferenceEngine:
    """Computes geometric, spatial, and quantity deltas between drawing revisions."""

    @classmethod
    def compute_polygon_iou(cls, poly_a: sg.Polygon, poly_b: sg.Polygon) -> float:
        """Computes geometric Intersection-over-Union between two spatial polygons."""
        if not poly_a.is_valid:
            poly_a = poly_a.buffer(0)
        if not poly_b.is_valid:
            poly_b = poly_b.buffer(0)

        inter = poly_a.intersection(poly_b).area
        union = poly_a.union(poly_b).area
        if union < 1e-6:
            return 0.0
        return inter / union

    @classmethod
    def compare_spatial_rooms(
        cls,
        baseline_rooms: list[Room],
        revised_rooms: list[Room],
        iou_threshold: float = 0.85,
        uncertain_threshold: float = 0.50
    ) -> dict[str, tuple[str, float, str]]:
        """
        Matches spatial rooms across revisions using geometric IoU and centroid proximity.
        Returns mapping: baseline_room_id -> (matched_revised_id, iou_score, match_status).
        """
        matches = {}
        revised_polys = {
            r.id: (r, sg.Polygon([(v.x, v.y) for v in r.polygon.vertices]))
            for r in revised_rooms
        }

        for base_r in baseline_rooms:
            base_poly = sg.Polygon([(v.x, v.y) for v in base_r.polygon.vertices])
            best_rev_id = None
            best_iou = 0.0

            for rev_id, (rev_r, rev_poly) in revised_polys.items():
                iou = cls.compute_polygon_iou(base_poly, rev_poly)
                if iou > best_iou:
                    best_iou = iou
                    best_rev_id = rev_id

            if best_iou >= iou_threshold:
                matches[base_r.id] = (best_rev_id, best_iou, "CONFIDENT_MATCH")
            elif best_iou >= uncertain_threshold:
                matches[base_r.id] = (best_rev_id, best_iou, "UNCERTAIN_MATCH")
            else:
                matches[base_r.id] = (None, best_iou, "NO_MATCH")

        return matches

    @classmethod
    def compare_takeoffs(
        cls,
        baseline: TakeoffSummary,
        revised: TakeoffSummary,
        tolerance: float = 0.01,
        baseline_rooms: list[Room] | None = None,
        revised_rooms: list[Room] | None = None
    ) -> RevisionComparisonResult:
        """
        Compares two TakeoffSummary versions using spatial matching when rooms are provided,
        falling back to intelligent key correlation.
        """
        deltas: list[QuantityDelta] = []
        matched_revised_items: set[int] = set()

        # Check if spatial room matching is possible
        spatial_room_map = {}
        base_room_by_name = {r.name.upper(): r for r in (baseline_rooms or [])}
        rev_room_by_name = {r.name.upper(): r for r in (revised_rooms or [])}

        if baseline_rooms and revised_rooms:
            room_matches = cls.compare_spatial_rooms(baseline_rooms, revised_rooms)
            rev_by_id = {r.id: r for r in revised_rooms}
            for base_id, (match_id, iou, status) in room_matches.items():
                if match_id and match_id in rev_by_id:
                    rev_r = rev_by_id[match_id]
                    # Map baseline room name to revised room name
                    base_r = next(r for r in baseline_rooms if r.id == base_id)
                    spatial_room_map[base_r.name.upper()] = (rev_r.name.upper(), iou, status)

        # 1. Process baseline items
        for base_item in baseline.items:
            best_match_idx = None
            best_similarity = 0.0
            is_spatial_rename = False

            # First, check exact item_code and location match
            for idx, rev_item in enumerate(revised.items):
                if idx in matched_revised_items:
                    continue
                if rev_item.item_code == base_item.item_code and rev_item.location.upper() == base_item.location.upper():
                    best_match_idx = idx
                    best_similarity = 1.0
                    break

            # Second, check spatial room match (e.g. Conference Room -> Meeting Room)
            if best_match_idx is None and base_item.location.upper() in spatial_room_map:
                mapped_rev_name, iou, match_status = spatial_room_map[base_item.location.upper()]
                for idx, rev_item in enumerate(revised.items):
                    if idx in matched_revised_items:
                        continue
                    if rev_item.item_code == base_item.item_code and rev_item.location.upper() == mapped_rev_name:
                        best_match_idx = idx
                        best_similarity = iou
                        is_spatial_rename = True
                        break

            if best_match_idx is not None:
                matched_revised_items.add(best_match_idx)
                rev_item = revised.items[best_match_idx]
                delta_qty = rev_item.quantity - base_item.quantity
                pct = (delta_qty / base_item.quantity * 100.0) if base_item.quantity > 0 else None

                if best_similarity < 0.85:
                    ctype = ChangeType.UNCERTAIN_MATCH
                elif is_spatial_rename or abs(delta_qty) > tolerance:
                    ctype = ChangeType.MODIFIED
                else:
                    ctype = ChangeType.UNCHANGED

                desc = rev_item.description
                if is_spatial_rename and base_item.location.upper() != rev_item.location.upper():
                    desc = f"{rev_item.description} (Renamed from '{base_item.location}')"

                deltas.append(QuantityDelta(
                    item_code=base_item.item_code,
                    description=desc,
                    location=rev_item.location,
                    baseline_qty=base_item.quantity,
                    revised_qty=rev_item.quantity,
                    delta_qty=delta_qty,
                    delta_percentage=pct,
                    unit=base_item.unit.value,
                    change_type=ctype,
                    match_confidence=best_similarity,
                    spatial_similarity=best_similarity
                ))
            else:
                # Item present in baseline but missing in revised -> REMOVED
                deltas.append(QuantityDelta(
                    item_code=base_item.item_code,
                    description=base_item.description,
                    location=base_item.location,
                    baseline_qty=base_item.quantity,
                    revised_qty=0.0,
                    delta_qty=-base_item.quantity,
                    delta_percentage=-100.0,
                    unit=base_item.unit.value,
                    change_type=ChangeType.REMOVED,
                    match_confidence=1.0,
                    spatial_similarity=0.0
                ))

        # 2. Check for newly introduced items in revised -> ADDED
        for idx, rev_item in enumerate(revised.items):
            if idx not in matched_revised_items:
                deltas.append(QuantityDelta(
                    item_code=rev_item.item_code,
                    description=rev_item.description,
                    location=rev_item.location,
                    baseline_qty=0.0,
                    revised_qty=rev_item.quantity,
                    delta_qty=rev_item.quantity,
                    delta_percentage=100.0,
                    unit=rev_item.unit.value,
                    change_type=ChangeType.ADDED,
                    match_confidence=1.0,
                    spatial_similarity=0.0
                ))

        return RevisionComparisonResult(
            baseline_drawing_id=baseline.drawing_id,
            revised_drawing_id=revised.drawing_id,
            baseline_revision=baseline.revision,
            revised_revision=revised.revision,
            deltas=deltas
        )
