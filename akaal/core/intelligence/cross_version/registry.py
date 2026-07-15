"""
Akaal — Cross-Version Compatibility Strategy Registry
======================================================
Thread-safe, lifecycle-managed registry with multi-indexing,
deterministic rule resolution, conflict detection, copy-on-write
snapshots, and hot-reload capability.
"""

import threading
from typing import Any, Dict, List, Optional, Tuple

from akaal.core.models.enums import SystemType
from akaal.core.intelligence.common.registry import BaseRegistry
from akaal.core.intelligence.common.exceptions import (
    RegistryDuplicateError,
    RegistryFrozenError,
)
from akaal.core.intelligence.cross_version.exceptions import (
    CompatibilityRegistryConflictError,
    VersionParseError,
)
from akaal.core.intelligence.cross_version.models import (
    CompatibilityRule,
    CompatibilityRuleAction,
)


# =============================================================================
# Version Parser (shared utility)
# =============================================================================

def _parse_version(version_str: Optional[str]) -> Tuple[int, ...]:
    """
    Parses a version string into a comparable integer tuple.
    Non-numeric components are silently skipped.
    Returns an empty tuple for None or empty input.
    """
    if not version_str:
        return ()
    parts = []
    for segment in version_str.split("."):
        try:
            parts.append(int(segment))
        except ValueError:
            pass
    return tuple(parts)


# =============================================================================
# Rule Matcher
# =============================================================================

class CompatibilityRuleMatcher:
    """
    Evaluates and ranks CompatibilityRules against a target context.
    Implements specificity scoring and deterministic priority resolution.
    """

    @classmethod
    def calculate_specificity(
        cls,
        rule: CompatibilityRule,
    ) -> int:
        """
        Scores rule specificity. More constrained rules rank higher.
        Version bounds: +10 each, target version constraint: +5.
        """
        score = 0
        if rule.min_source_version:
            score += 10
        if rule.max_source_version:
            score += 10
        if rule.min_target_version:
            score += 5
        if rule.max_target_version:
            score += 5
        return score

    @classmethod
    def matches(
        cls,
        rule: CompatibilityRule,
        source_dialect: SystemType,
        target_dialect: SystemType,
        source_version: str,
        target_version: str,
    ) -> bool:
        """
        Returns True if the rule applies to the given migration context.
        Evaluates source/target dialect, source version bounds, and
        target version bounds.
        """
        if rule.source_dialect != source_dialect:
            return False
        if rule.target_dialect != target_dialect:
            return False

        src_v = _parse_version(source_version)

        if rule.min_source_version:
            if src_v < _parse_version(rule.min_source_version):
                return False
        if rule.max_source_version:
            if src_v > _parse_version(rule.max_source_version):
                return False

        tgt_v = _parse_version(target_version)

        if rule.min_target_version:
            if tgt_v < _parse_version(rule.min_target_version):
                return False
        if rule.max_target_version:
            if tgt_v > _parse_version(rule.max_target_version):
                return False

        return True

    @classmethod
    def match_rules(
        cls,
        rules: List[CompatibilityRule],
        source_dialect: SystemType,
        target_dialect: SystemType,
        source_version: str,
        target_version: str,
    ) -> List[CompatibilityRule]:
        """
        Returns all matching rules, sorted by descending specificity then
        descending priority with rule_id as a stable tie-breaker.
        """
        matched = [
            r for r in rules
            if cls.matches(r, source_dialect, target_dialect, source_version, target_version)
        ]

        def sort_key(r: CompatibilityRule) -> Tuple[int, int, str]:
            return (-cls.calculate_specificity(r), -r.priority, r.rule_id)

        matched.sort(key=sort_key)
        return matched

    @classmethod
    def detect_conflicts(
        cls,
        rule1: CompatibilityRule,
        rule2: CompatibilityRule,
    ) -> None:
        """
        Detects overlapping rules that share the same feature_id,
        source/target dialect pair, overlapping version ranges,
        and identical priority. Raises CompatibilityRegistryConflictError
        if an unresolvable conflict is found.
        """
        if rule1.feature_id != rule2.feature_id:
            return
        if rule1.source_dialect != rule2.source_dialect:
            return
        if rule1.target_dialect != rule2.target_dialect:
            return

        # Check source version overlap
        src_overlap = cls._version_ranges_overlap(
            rule1.min_source_version, rule1.max_source_version,
            rule2.min_source_version, rule2.max_source_version,
        )

        if src_overlap and rule1.priority == rule2.priority:
            raise CompatibilityRegistryConflictError(
                f"Conflict between rules '{rule1.rule_id}' and '{rule2.rule_id}': "
                f"Both match feature '{rule1.feature_id}' on "
                f"{rule1.source_dialect.value} -> {rule1.target_dialect.value} "
                f"with equal priority {rule1.priority}.",
                error_code="COMPATIBILITY_RULE_CONFLICT",
            )

    @staticmethod
    def _version_ranges_overlap(
        min1: Optional[str],
        max1: Optional[str],
        min2: Optional[str],
        max2: Optional[str],
    ) -> bool:
        """Returns True if two half-open version ranges overlap."""
        if max1 and min2:
            if _parse_version(max1) < _parse_version(min2):
                return False
        if max2 and min1:
            if _parse_version(max2) < _parse_version(min1):
                return False
        return True


# =============================================================================
# Compatibility Strategy Registry
# =============================================================================

class CompatibilityStrategyRegistry(BaseRegistry[CompatibilityRule]):
    """
    Thread-safe registry with multi-dimensional indexes for O(1) lookups
    by feature_id, source dialect, target dialect, and action type.

    Lifecycle:
        bootstrap -> validate -> conflict_check -> freeze -> snapshot/hot_reload
    """

    def __init__(self, version: str = "1.0.0") -> None:
        super().__init__(version=version)
        self._lock = threading.RLock()

        # Multi-dimensional indexes
        self._by_rule_id: Dict[str, CompatibilityRule] = {}
        self._by_feature_id: Dict[str, List[CompatibilityRule]] = {}
        self._by_source_dialect: Dict[SystemType, List[CompatibilityRule]] = {}
        self._by_target_dialect: Dict[SystemType, List[CompatibilityRule]] = {}
        self._by_action: Dict[CompatibilityRuleAction, List[CompatibilityRule]] = {}

    # ------------------------------------------------------------------
    # BaseRegistry abstract methods
    # ------------------------------------------------------------------

    def _validate_rule(self, rule: CompatibilityRule) -> None:
        if not rule.rule_id:
            raise ValueError("CompatibilityRule.rule_id must be non-empty.")
        if not rule.rule_name:
            raise ValueError("CompatibilityRule.rule_name must be non-empty.")
        if not rule.feature_id:
            raise ValueError("CompatibilityRule.feature_id must be non-empty.")
        if not (1 <= rule.priority <= 1000):
            raise ValueError(f"Rule priority must be 1..1000, got {rule.priority}.")

    def _detect_conflicts(self, new_rule_id: str, new_rule: CompatibilityRule) -> None:
        for existing_id, existing_rule in self._by_rule_id.items():
            if existing_id != new_rule_id:
                CompatibilityRuleMatcher.detect_conflicts(new_rule, existing_rule)

    def _check_conflict_between(
        self,
        id1: str,
        rule1: CompatibilityRule,
        id2: str,
        rule2: CompatibilityRule,
    ) -> None:
        CompatibilityRuleMatcher.detect_conflicts(rule1, rule2)

    def _sort_key(self, rule: CompatibilityRule) -> Any:
        spec = CompatibilityRuleMatcher.calculate_specificity(rule)
        return (-spec, -rule.priority, rule.rule_id)

    # ------------------------------------------------------------------
    # Registration (overrides BaseRegistry to rebuild indexes)
    # ------------------------------------------------------------------

    def register(self, rule_id: str, rule: CompatibilityRule) -> None:
        """Registers a rule thread-safely and rebuilds all multi-indexes."""
        with self._lock:
            if self._frozen:
                raise RegistryFrozenError(
                    f"Registry is frozen. Cannot register rule '{rule_id}'.",
                    error_code="REGISTRY_FROZEN",
                )
            if rule_id in self._by_rule_id:
                raise RegistryDuplicateError(
                    f"Duplicate rule ID: '{rule_id}'.",
                    error_code="REGISTRY_DUPLICATE",
                )

            self._validate_rule(rule)
            self._detect_conflicts(rule_id, rule)

            self._by_rule_id[rule_id] = rule
            self._rules[rule_id] = rule  # keep BaseRegistry in sync

            # Update indexes
            self._by_feature_id.setdefault(rule.feature_id, []).append(rule)
            self._by_source_dialect.setdefault(rule.source_dialect, []).append(rule)
            self._by_target_dialect.setdefault(rule.target_dialect, []).append(rule)
            self._by_action.setdefault(rule.action, []).append(rule)

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_rule(self, rule_id: str) -> Optional[CompatibilityRule]:
        """Returns the rule for a given ID, or None."""
        if self._frozen:
            return self._by_rule_id.get(rule_id)
        with self._lock:
            return self._by_rule_id.get(rule_id)

    def list_rules(self) -> List[CompatibilityRule]:
        """Returns all registered rules in deterministic order."""
        if self._frozen:
            rules = list(self._by_rule_id.values())
        else:
            with self._lock:
                rules = list(self._by_rule_id.values())
        return sorted(rules, key=self._sort_key)

    def get_rules_for_feature(self, feature_id: str) -> List[CompatibilityRule]:
        """Returns all rules that apply to a specific feature."""
        if self._frozen:
            return list(self._by_feature_id.get(feature_id, []))
        with self._lock:
            return list(self._by_feature_id.get(feature_id, []))

    def get_rules_for_source_dialect(self, dialect: SystemType) -> List[CompatibilityRule]:
        """Returns all rules matching a specific source dialect."""
        if self._frozen:
            return list(self._by_source_dialect.get(dialect, []))
        with self._lock:
            return list(self._by_source_dialect.get(dialect, []))

    def get_rules_for_target_dialect(self, dialect: SystemType) -> List[CompatibilityRule]:
        """Returns all rules matching a specific target dialect."""
        if self._frozen:
            return list(self._by_target_dialect.get(dialect, []))
        with self._lock:
            return list(self._by_target_dialect.get(dialect, []))

    def get_rules_by_action(self, action: CompatibilityRuleAction) -> List[CompatibilityRule]:
        """Returns all rules with a specific action type."""
        if self._frozen:
            return list(self._by_action.get(action, []))
        with self._lock:
            return list(self._by_action.get(action, []))

    def get_matching_rules(
        self,
        source_dialect: SystemType,
        target_dialect: SystemType,
        source_version: str,
        target_version: str,
    ) -> List[CompatibilityRule]:
        """
        Returns all rules matching the migration context, ordered by
        descending specificity then descending priority.
        """
        if self._frozen:
            all_rules = list(self._by_rule_id.values())
        else:
            with self._lock:
                all_rules = list(self._by_rule_id.values())

        return CompatibilityRuleMatcher.match_rules(
            all_rules, source_dialect, target_dialect,
            source_version, target_version,
        )

    # ------------------------------------------------------------------
    # Snapshot / Hot-Reload
    # ------------------------------------------------------------------

    def snapshot(self) -> "CompatibilityStrategyRegistry":
        """
        Creates a mutable copy-on-write snapshot of the registry.
        The snapshot is independent and can be modified or frozen separately.
        """
        with self._lock:
            snap = CompatibilityStrategyRegistry(version=self._version)
            for rid, rule in self._by_rule_id.items():
                snap.register(rid, rule)
            return snap

    def hot_reload(self, rules_dict: Dict[str, CompatibilityRule]) -> None:
        """
        Atomically replaces the entire rule set.
        Validates all new rules in isolation before swapping pointers.
        Cannot be called on a frozen registry.
        """
        with self._lock:
            if self._frozen:
                raise RegistryFrozenError(
                    "Cannot hot-reload a frozen registry.",
                    error_code="REGISTRY_FROZEN_RELOAD",
                )
            # Build and validate a candidate registry first
            candidate = CompatibilityStrategyRegistry(version=self._version)
            for rid, rule in rules_dict.items():
                candidate.register(rid, rule)

            # Atomic pointer swap
            self._by_rule_id = candidate._by_rule_id
            self._by_feature_id = candidate._by_feature_id
            self._by_source_dialect = candidate._by_source_dialect
            self._by_target_dialect = candidate._by_target_dialect
            self._by_action = candidate._by_action
            self._rules = candidate._rules
