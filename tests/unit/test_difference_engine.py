"""
Unit Tests for Revision Difference Engine & Delta Categorization
"""

import pytest
from core.models.takeoff import TakeoffSummary, TakeoffLineItem
from core.units import DisplayUnit
from revision.difference_engine import RevisionDifferenceEngine
from revision.models import ChangeType

def test_difference_engine_all_change_types():
    # Baseline: Rev 01
    baseline = TakeoffSummary(
        drawing_id="DRW-BASE-01",
        drawing_number="A-101",
        revision="01",
        items=[
            TakeoffLineItem(
                id="TO-1", item_code="FL-01", description="Flooring",
                location="Conference Room", quantity=24.0, unit=DisplayUnit.SQM, formula="24 sqm"
            ),
            TakeoffLineItem(
                id="TO-2", item_code="FL-01", description="Flooring",
                location="Old Storeroom", quantity=10.0, unit=DisplayUnit.SQM, formula="10 sqm"
            ),
            TakeoffLineItem(
                id="TO-3", item_code="FL-01", description="Flooring",
                location="Executive Cabin", quantity=16.0, unit=DisplayUnit.SQM, formula="16 sqm"
            ),
        ]
    )

    # Revised: Rev 02
    # - Conference Room expanded from 24 -> 30 sqm (MODIFIED)
    # - Old Storeroom deleted (REMOVED)
    # - Executive Cabin unchanged at 16 sqm (UNCHANGED)
    # - New Pantry added at 8 sqm (ADDED)
    revised = TakeoffSummary(
        drawing_id="DRW-REV-02",
        drawing_number="A-101",
        revision="02",
        items=[
            TakeoffLineItem(
                id="TO-1", item_code="FL-01", description="Flooring",
                location="Conference Room", quantity=30.0, unit=DisplayUnit.SQM, formula="30 sqm"
            ),
            TakeoffLineItem(
                id="TO-3", item_code="FL-01", description="Flooring",
                location="Executive Cabin", quantity=16.0, unit=DisplayUnit.SQM, formula="16 sqm"
            ),
            TakeoffLineItem(
                id="TO-4", item_code="FL-01", description="Flooring",
                location="New Pantry", quantity=8.0, unit=DisplayUnit.SQM, formula="8 sqm"
            ),
        ]
    )

    result = RevisionDifferenceEngine.compare_takeoffs(baseline, revised)

    assert len(result.deltas) == 4
    delta_dict = {d.location: d for d in result.deltas}

    # 1. Conference Room: MODIFIED
    conf = delta_dict["Conference Room"]
    assert conf.change_type == ChangeType.MODIFIED
    assert conf.baseline_qty == 24.0
    assert conf.revised_qty == 30.0
    assert conf.delta_qty == 6.0
    assert pytest.approx(conf.delta_percentage) == 25.0

    # 2. Executive Cabin: UNCHANGED
    cabin = delta_dict["Executive Cabin"]
    assert cabin.change_type == ChangeType.UNCHANGED
    assert cabin.delta_qty == 0.0

    # 3. Old Storeroom: REMOVED
    store = delta_dict["Old Storeroom"]
    assert store.change_type == ChangeType.REMOVED
    assert store.delta_qty == -10.0

    # 4. New Pantry: ADDED
    pantry = delta_dict["New Pantry"]
    assert pantry.change_type == ChangeType.ADDED
    assert pantry.delta_qty == 8.0

    # Summary counts
    assert len(result.modified_items) == 1
    assert len(result.unchanged_items) == 1
    assert len(result.removed_items) == 1
    assert len(result.added_items) == 1
    # Net delta: +6 -10 +8 = +4 sqm
    assert pytest.approx(result.net_area_delta_sqm) == 4.0
