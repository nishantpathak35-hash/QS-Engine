"""
QS Quantification Engine — Project Profile Configuration Model
Enforces Blueprint Section 45 and Section 80: Explicit configuration, assumption approvals, and trade mappings.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProjectProfile:
    """Explicit project-level configuration and assumption approvals."""
    project_id: str = "DEFAULT"
    profile_version: str = "1.0.0"
    units: str = "mm"
    active_rule_profile: str | None = None
    allow_assumptions: bool = False
    approved_assumptions: dict[str, Any] = field(default_factory=dict)
    room_finish_mapping_enabled: bool = False
    room_finish_mapping: dict[str, str] = field(default_factory=dict)
    skirting_finish_mapping: dict[str, str] = field(default_factory=dict)
    ceiling_finish_mapping: dict[str, str] = field(default_factory=dict)
    door_type_mapping: dict[str, str] = field(default_factory=dict)
    ceiling_height_m: float | None = None
    default_door_width_mm: float | None = None
    default_door_height_mm: float | None = None
    wastage_enabled: bool = True
    wastage_preset: str = "standard"  # "standard", "conservative", "tight", "zero"
    custom_wastage_factors: dict[str, float] = field(default_factory=dict)

    @classmethod
    def create_strict_default(cls) -> ProjectProfile:
        """Creates a zero-guesswork strict project profile."""
        return cls(
            project_id="DEFAULT_STRICT",
            units="mm",
            active_rule_profile=None,
            allow_assumptions=False,
            room_finish_mapping_enabled=False,
            approved_assumptions={},
            room_finish_mapping={},
            skirting_finish_mapping={},
            ceiling_finish_mapping={},
            door_type_mapping={},
            wastage_enabled=True,
            wastage_preset="standard",
            custom_wastage_factors={}
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ProjectProfile:
        """Creates a ProjectProfile from dict, handling nested keys and YAML aliases."""
        if not data:
            return cls.create_strict_default()
        d = data.get("project_profile", data).copy()
        if "profile_id" in d and "project_id" not in d:
            d["project_id"] = d.pop("profile_id")
        if "measurement_profile" in d and "active_rule_profile" not in d:
            mp = d.pop("measurement_profile")
            if not mp.endswith(".yaml") and not mp.endswith(".yml"):
                mp = f"{mp}.yaml"
            d["active_rule_profile"] = mp
        if "assumptions_enabled" in d and "allow_assumptions" not in d:
            d["allow_assumptions"] = d.pop("assumptions_enabled")

        known_fields = {
            "project_id", "profile_version", "units", "active_rule_profile",
            "allow_assumptions", "approved_assumptions", "room_finish_mapping_enabled",
            "room_finish_mapping", "skirting_finish_mapping", "ceiling_finish_mapping",
            "door_type_mapping", "ceiling_height_m", "default_door_width_mm", "default_door_height_mm",
            "wastage_enabled", "wastage_preset", "custom_wastage_factors"
        }
        filtered = {k: v for k, v in d.items() if k in known_fields}
        return cls(**filtered)

    def get_wastage_percent(self, item_code: str, description: str = "") -> float:
        """Determines the standard trade wastage factor for procurement calculations."""
        if not self.wastage_enabled or self.wastage_preset == "zero":
            return 0.0

        if item_code in self.custom_wastage_factors:
            return float(self.custom_wastage_factors[item_code])

        code_u = item_code.upper()
        desc_u = description.upper()

        mult = 1.0
        if self.wastage_preset == "conservative":
            mult = 1.4
        elif self.wastage_preset == "tight":
            mult = 0.6

        # Flooring
        if code_u.startswith("FL-") or "FLOOR" in desc_u or "TILE" in desc_u or "CARPET" in desc_u:
            return round(0.05 * mult, 3)
        # Ceiling
        elif code_u.startswith("CL-") or "CEILING" in desc_u:
            return round(0.05 * mult, 3)
        # Partitions
        elif code_u.startswith("PT-") or "PARTITION" in desc_u or "WALL" in desc_u:
            return round(0.07 * mult, 3)
        # Skirting
        elif code_u.startswith("SK-") or "SKIRTING" in desc_u:
            return round(0.05 * mult, 3)
        # Painting & Wall Finishes
        elif "PAINT" in desc_u or "PUNNING" in desc_u or "FINISH" in desc_u:
            return round(0.08 * mult, 3)
        # Light Fixtures (Commissioning / Spares)
        elif code_u.startswith("LT-") or "LIGHT" in desc_u:
            return round(0.03 * mult, 3)
        # Furniture / Workstations
        elif code_u.startswith("FN-") or "WORKSTATION" in desc_u or "CHAIR" in desc_u or "SEAT" in desc_u:
            return 0.0
        # Doors
        elif code_u.startswith("DR-") or "DOOR" in desc_u:
            return 0.0

        return round(0.05 * mult, 3)

    def is_assumption_approved(self, key: str) -> bool:
        """Checks if a specific dimension/trade assumption is explicitly approved for this project."""
        if not self.allow_assumptions:
            return False
        if isinstance(self.approved_assumptions, (list, set)):
            return key in self.approved_assumptions
        if isinstance(self.approved_assumptions, dict):
            return key in self.approved_assumptions and self.approved_assumptions[key] is not None
        return False

    def get_approved_dimension(self, key: str, fallback: float | None = None) -> float | None:
        """Returns the approved assumption value if enabled and approved; otherwise None."""
        if not self.is_assumption_approved(key):
            return fallback
        if isinstance(self.approved_assumptions, dict) and key in self.approved_assumptions:
            val = self.approved_assumptions[key]
            if val is not None:
                return float(val)
        if key == "default_ceiling_height_m" and self.ceiling_height_m is not None:
            return float(self.ceiling_height_m)
        if key == "default_door_width_mm" and self.default_door_width_mm is not None:
            return float(self.default_door_width_mm)
        if key == "default_door_height_mm" and self.default_door_height_mm is not None:
            return float(self.default_door_height_mm)
        return fallback
