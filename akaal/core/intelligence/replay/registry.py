"""
Akaal — Replay Provider Registry
===============================
Implements the provider registries for CDC extractors and replayers,
inheriting from the base reentrant registry framework.
"""

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from akaal.core.models.enums import SystemType
from akaal.core.intelligence.common.exceptions import ConflictResolutionError
from akaal.core.intelligence.common.registry import BaseRegistry


@dataclass(frozen=True)
class CDCProviderMetadata:
    """Immutable representation of a dynamic replay provider descriptor."""
    provider_id: str
    provider_name: str
    dialect: SystemType
    priority: int
    version: str


class ReplayProviderRegistry(BaseRegistry[CDCProviderMetadata]):
    """Reentrant registry of replay drivers sorted deterministically by evaluation priorities."""
    def _validate_rule(self, rule: CDCProviderMetadata) -> None:
        if not rule.provider_id or not rule.provider_name:
            raise ValueError("Provider ID and name must be defined.")

    def _detect_conflicts(self, new_rule_id: str, new_rule: CDCProviderMetadata) -> None:
        for r_id, r in self._rules.items():
            if r_id != new_rule_id:
                self._check_conflict_between(new_rule_id, new_rule, r_id, r)

    def _check_conflict_between(
        self,
        id1: str,
        rule1: CDCProviderMetadata,
        id2: str,
        rule2: CDCProviderMetadata
    ) -> None:
        if rule1.dialect == rule2.dialect and rule1.provider_name == rule2.provider_name:
            raise ConflictResolutionError(
                f"Conflict between '{id1}' and '{id2}': both register provider '{rule1.provider_name}' for '{rule1.dialect.value}'.",
                error_code="PROVIDER_CONFLICT"
            )

    def _sort_key(self, rule: CDCProviderMetadata) -> Any:
        # Priority descending, then tie-break on ID
        return (-rule.priority, rule.provider_id)
