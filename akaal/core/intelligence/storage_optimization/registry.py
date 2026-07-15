"""
Akaal — Storage Rules Registry
==============================
Implements the storage rule mappings, conflict preventions, and reentrant registry blocks.
"""

from dataclasses import dataclass
from typing import Any

from akaal.core.models.enums import SystemType
from akaal.core.intelligence.common.exceptions import ConflictResolutionError
from akaal.core.intelligence.common.registry import BaseRegistry


@dataclass(frozen=True)
class StorageRuleMetadata:
    """Immutable metadata representing custom tablespace placement or sizing rules."""
    rule_id: str
    rule_name: str
    target_dialect: SystemType
    priority: int
    rule_type: str  # e.g., "TABLESPACE", "PARTITION"
    metadata_value: str


class StorageRulesRegistry(BaseRegistry[StorageRuleMetadata]):
    """Reentrant registry of storage placement guidelines sorted deterministically."""
    def _validate_rule(self, rule: StorageRuleMetadata) -> None:
        if not rule.rule_id or not rule.rule_name:
            raise ValueError("Rule ID and Name must be defined.")

    def _detect_conflicts(self, new_rule_id: str, new_rule: StorageRuleMetadata) -> None:
        for r_id, r in self._rules.items():
            if r_id != new_rule_id:
                self._check_conflict_between(new_rule_id, new_rule, r_id, r)

    def _check_conflict_between(
        self,
        id1: str,
        rule1: StorageRuleMetadata,
        id2: str,
        rule2: StorageRuleMetadata
    ) -> None:
        if rule1.target_dialect == rule2.target_dialect and rule1.rule_name == rule2.rule_name:
            raise ConflictResolutionError(
                f"Conflict between '{id1}' and '{id2}': both register rule '{rule1.rule_name}' for '{rule1.target_dialect.value}'.",
                error_code="STORAGE_RULE_CONFLICT"
            )

    def _sort_key(self, rule: StorageRuleMetadata) -> Any:
        return (-rule.priority, rule.rule_id)
