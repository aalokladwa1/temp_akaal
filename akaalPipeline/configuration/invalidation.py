"""akaalPipeline.configuration.invalidation
===========================================
Material change classification and invalidation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Set


class MaterialChangeClassification(str, Enum):
    NONE = "NONE"
    MINOR = "MINOR"
    MATERIAL = "MATERIAL"


# Settings that constitute material changes requiring invalidation of initializations & approvals
MATERIAL_SETTINGS: Set[str] = {
    "source_connection",
    "target_connection",
    "mode",
    "selected_tables",
    "schema_mappings",
    "cdc_slot",
    "validation_level",
}


@dataclass(frozen=True)
class InvalidationEffect:
    classification: MaterialChangeClassification
    invalidates_plan: bool
    invalidates_approval: bool
    invalidates_initialization: bool
    invalidates_schedule: bool
    changed_keys: Set[str]


class ConfigurationInvalidator:
    @staticmethod
    def classify_change(
        old_config: Mapping[str, Any],
        new_config: Mapping[str, Any],
    ) -> InvalidationEffect:
        changed_keys: Set[str] = set()

        all_keys = set(old_config.keys()) | set(new_config.keys())
        for k in all_keys:
            if old_config.get(k) != new_config.get(k):
                changed_keys.add(k)

        if not changed_keys:
            return InvalidationEffect(
                classification=MaterialChangeClassification.NONE,
                invalidates_plan=False,
                invalidates_approval=False,
                invalidates_initialization=False,
                invalidates_schedule=False,
                changed_keys=set(),
            )

        has_material = bool(changed_keys & MATERIAL_SETTINGS)

        if has_material:
            return InvalidationEffect(
                classification=MaterialChangeClassification.MATERIAL,
                invalidates_plan=True,
                invalidates_approval=True,
                invalidates_initialization=True,
                invalidates_schedule=True,
                changed_keys=changed_keys,
            )

        return InvalidationEffect(
            classification=MaterialChangeClassification.MINOR,
            invalidates_plan=False,
            invalidates_approval=False,
            invalidates_initialization=False,
            invalidates_schedule=False,
            changed_keys=changed_keys,
        )
