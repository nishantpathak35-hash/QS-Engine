"""
Adversarial Tests — Phase-1 True Spatial Revision Difference Engine
Validates:
1. Spatial room matching when room name changes (Conference Room -> Meeting Room) with identical geometry.
2. High IoU spatial match classified as MODIFIED (rename) instead of REMOVED + ADDED.
3. Partial spatial overlap (0.50 <= IoU < 0.85) flagged as UNCERTAIN_MATCH.
4. Spatial similarity metrics stored on QuantityDelta.
"""

import pytest
from core.geometry.primitives import Point2D, Polygon2D
from core.models.semantics import Room
from core.models.takeoff import TakeoffSummary, TakeoffLineItem
from core.units import DisplayUnit
from revision.difference_engine import RevisionDifferenceEngine
from revision.models import ChangeType


def test_spatial_room_rename_with_identical_geometry():
    """Room renamed from 'Conference Room' to 'Boardroom' with same geometry must be recognized as MODIFIED (rename)."""
    poly = Polygon2D([Point2D(0, 0), Point2D(6000, 0), Point2D(6000, 4000), Point2D(0, 4000)])
    base_room = Room(id="R-BASE-01", name="Conference Room", polygon=poly)
    rev_room = Room(id="R-REV-01", name="Boardroom", polygon=poly)

    base_takeoff = TakeoffSummary(
        drawing_id="DRW-01", drawing_number="A-101", revision="01",
        items=[
            TakeoffLineItem(
                id="TO-01", item_code="FL-01", description="Vitrified Tile Flooring",
                location="Conference Room", quantity=24.0, unit=DisplayUnit.SQM, formula="24 sqm"
            )
        ]
    )

    rev_takeoff = TakeoffSummary(
        drawing_id="DRW-02", drawing_number="A-101", revision="02",
        items=[
            TakeoffLineItem(
                id="TO-01", item_code="FL-01", description="Vitrified Tile Flooring",
                location="Boardroom", quantity=24.0, unit=DisplayUnit.SQM, formula="24 sqm"
            )
        ]
    )

    result = RevisionDifferenceEngine.compare_takeoffs(
        base_takeoff, rev_takeoff,
        baseline_rooms=[base_room], revised_rooms=[rev_room]
    )

    # Must NOT produce 1 REMOVED and 1 ADDED; must produce 1 MODIFIED (spatial rename)
    assert len(result.deltas) == 1
    delta = result.deltas[0]
    assert delta.change_type == ChangeType.MODIFIED
    assert delta.location == "Boardroom"
    assert "Renamed from 'Conference Room'" in delta.description
    assert delta.spatial_similarity >= 0.99


def test_uncertain_spatial_overlap_flagged_uncertain_match():
    """When a space is heavily reconfigured with 60% IoU, change_type must be UNCERTAIN_MATCH."""
    poly_base = Polygon2D([Point2D(0, 0), Point2D(10000, 0), Point2D(10000, 10000), Point2D(0, 10000)])
    # Shifted/resized space with ~54% IoU (70/130)
    poly_rev = Polygon2D([Point2D(3000, 0), Point2D(13000, 0), Point2D(13000, 10000), Point2D(3000, 10000)])

    base_room = Room(id="R-BASE-01", name="Zone A", polygon=poly_base)
    rev_room = Room(id="R-REV-01", name="Zone B", polygon=poly_rev)

    base_takeoff = TakeoffSummary(
        drawing_id="DRW-01", drawing_number="A-101", revision="01",
        items=[
            TakeoffLineItem(
                id="TO-01", item_code="FL-01", description="Flooring",
                location="Zone A", quantity=100.0, unit=DisplayUnit.SQM, formula="100 sqm"
            )
        ]
    )
    rev_takeoff = TakeoffSummary(
        drawing_id="DRW-02", drawing_number="A-101", revision="02",
        items=[
            TakeoffLineItem(
                id="TO-01", item_code="FL-01", description="Flooring",
                location="Zone B", quantity=100.0, unit=DisplayUnit.SQM, formula="100 sqm"
            )
        ]
    )

    result = RevisionDifferenceEngine.compare_takeoffs(
        base_takeoff, rev_takeoff,
        baseline_rooms=[base_room], revised_rooms=[rev_room]
    )

    assert len(result.deltas) == 1
    delta = result.deltas[0]
    assert delta.change_type == ChangeType.UNCERTAIN_MATCH
    assert 0.50 <= delta.spatial_similarity < 0.85
