"""
QS Quantification Engine — Dependency Graph & Lineage Status Propagation
Enforces Blueprint Section 37 and Sprint 3 Production Hardening:
- Downstream quantities must inherit and propagate unresolved or review_required statuses.
- No downstream quantity can remain AUTO_MEASURED if any prerequisite is unresolved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Sequence
from core.models.semantics import EntityStatus


@dataclass
class DependencyNode:
    """Represents a node in the quantity dependency graph."""
    node_id: str
    entity_type: str
    status: EntityStatus = EntityStatus.AUTO_MEASURED
    is_provisional: bool = False
    dependencies: list[DependencyNode] = field(default_factory=list)

    def resolve_effective_status(self) -> EntityStatus:
        """Propagates statuses through upstream dependencies."""
        if not self.dependencies:
            if self.is_provisional and self.status == EntityStatus.AUTO_MEASURED:
                return EntityStatus.REVIEW_REQUIRED
            return self.status

        child_statuses = [dep.resolve_effective_status() for dep in self.dependencies]

        # Critical failure / blocked propagation
        if any(s in (EntityStatus.UNRESOLVED, EntityStatus.REJECTED) for s in child_statuses):
            return EntityStatus.UNRESOLVED

        # Uncertainty / review propagation
        if any(s == EntityStatus.REVIEW_REQUIRED for s in child_statuses) or self.is_provisional:
            return EntityStatus.REVIEW_REQUIRED

        # If base is review required, preserve it
        if self.status == EntityStatus.REVIEW_REQUIRED:
            return EntityStatus.REVIEW_REQUIRED

        if all(s == EntityStatus.VERIFIED for s in child_statuses) and self.status == EntityStatus.VERIFIED:
            return EntityStatus.VERIFIED

        return self.status


def propagate_dependency_status(
    base_status: EntityStatus,
    prerequisite_statuses: Sequence[EntityStatus],
    has_provisional_inputs: bool = False
) -> EntityStatus:
    """
    Computes effective status given a base status and a list of upstream prerequisite statuses.
    Enforces that unverified or provisional upstream inputs downgrade AUTO_MEASURED to REVIEW_REQUIRED.
    """
    if any(s in (EntityStatus.UNRESOLVED, EntityStatus.REJECTED) for s in prerequisite_statuses):
        return EntityStatus.UNRESOLVED

    if has_provisional_inputs or any(s == EntityStatus.REVIEW_REQUIRED for s in prerequisite_statuses):
        return EntityStatus.REVIEW_REQUIRED

    if base_status == EntityStatus.REVIEW_REQUIRED:
        return EntityStatus.REVIEW_REQUIRED

    return base_status
