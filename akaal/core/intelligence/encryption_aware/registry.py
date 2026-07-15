"""
Akaal — Encryption Rules Registry
=================================
Manages dialect strategy rules, version constraints, and target algorithm matching.
"""

import threading
from typing import Any, Dict, List, Optional, Set, Tuple

from akaal.core.models.enums import SystemType
from akaal.core.intelligence.common.registry import BaseRegistry
from akaal.core.intelligence.common.exceptions import (
    RegistryDuplicateError,
    RegistryFrozenError,
)
from akaal.core.intelligence.encryption_aware.exceptions import EncryptionRegistryConflictError
from akaal.core.intelligence.encryption_aware.models import (
    EncryptionRule,
    EncryptionAlgorithm,
    KeyManagementProvider,
)

class EncryptionRuleMatcher:
    """Computes version specificity matching, dialect priorities, and checks conflicts."""

    @staticmethod
    def _parse_version(version_str: Optional[str]) -> Tuple[int, ...]:
        if not version_str:
            return ()
        parts = []
        for p in version_str.split("."):
            try:
                parts.append(int(p))
            except ValueError:
                pass
        return tuple(parts)

    @classmethod
    def calculate_specificity(
        cls,
        rule: EncryptionRule,
        version: str,
        engine: str,
        edition: str
    ) -> int:
        """Determines constraint specificity score. Higher means more narrow rules match."""
        score = 0
        if rule.min_version or rule.max_version:
            score += 10
        if rule.required_engine:
            score += 5
        if rule.required_edition:
            score += 5
        return score

    @classmethod
    def matches(
        cls,
        rule: EncryptionRule,
        dialect: SystemType,
        version: str,
        engine: str,
        edition: str
    ) -> bool:
        """Evaluates version boundaries, engine, and edition constraints."""
        if rule.target_dialect != dialect:
            return False

        if rule.required_engine and rule.required_engine.lower() != engine.lower():
            return False

        if rule.required_edition and rule.required_edition.lower() != edition.lower():
            return False

        # Version boundaries check
        v_parts = cls._parse_version(version)
        if rule.min_version:
            min_parts = cls._parse_version(rule.min_version)
            if v_parts < min_parts:
                return False

        if rule.max_version:
            max_parts = cls._parse_version(rule.max_version)
            if v_parts > max_parts:
                return False

        return True

    @classmethod
    def match_rules(
        cls,
        rules: List[EncryptionRule],
        dialect: SystemType,
        version: str,
        engine: str,
        edition: str
    ) -> List[EncryptionRule]:
        """Resolves applicable rules matching context, ordered by specificity and priority."""
        matched = [r for r in rules if cls.matches(r, dialect, version, engine, edition)]

        def sort_key(r: EncryptionRule) -> Any:
            spec = cls.calculate_specificity(r, version, engine, edition)
            return (-spec, -r.priority, r.rule_id)

        matched.sort(key=sort_key)
        return matched

    @classmethod
    def detect_conflicts(cls, rule1: EncryptionRule, rule2: EncryptionRule) -> None:
        """Audits overlap boundaries to ensure rule resolution remains deterministic."""
        if rule1.target_dialect != rule2.target_dialect:
            return

        engine_overlap = True
        if rule1.required_engine and rule2.required_engine:
            engine_overlap = rule1.required_engine.upper() == rule2.required_engine.upper()

        edition_overlap = True
        if rule1.required_edition and rule2.required_edition:
            edition_overlap = rule1.required_edition.upper() == rule2.required_edition.upper()

        if engine_overlap and edition_overlap:
            ver_overlap = True
            if rule1.max_version and rule2.min_version:
                if rule1.max_version < rule2.min_version:
                    ver_overlap = False
            if rule2.max_version and rule1.min_version:
                if rule2.max_version < rule1.min_version:
                    ver_overlap = False

            if ver_overlap and rule1.priority == rule2.priority:
                raise EncryptionRegistryConflictError(
                    f"Conflict detected between rules '{rule1.rule_id}' and '{rule2.rule_id}': "
                    f"Overlapping context boundaries with matching priority {rule1.priority}.",
                    error_code="ENCRYPTION_RULE_CONFLICT"
                )

class EncryptionStrategyRegistry(BaseRegistry[EncryptionRule]):
    """Extensible thread-safe registry with multi-indexing keys."""

    def __init__(self, version: str = "1.0.0") -> None:
        super().__init__(version=version)
        self._lock = threading.RLock()

        # Multi-indexes
        self._by_rule_id: Dict[str, EncryptionRule] = {}
        self._by_algorithm: Dict[EncryptionAlgorithm, List[EncryptionRule]] = {}
        self._by_dialect: Dict[SystemType, List[EncryptionRule]] = {}
        self._by_provider: Dict[KeyManagementProvider, List[EncryptionRule]] = {}
        self._by_version: Dict[str, List[EncryptionRule]] = {}
        self._by_edition: Dict[str, List[EncryptionRule]] = {}
        self._by_key_management_provider: Dict[KeyManagementProvider, List[EncryptionRule]] = {}

    def _validate_rule(self, rule: EncryptionRule) -> None:
        if not rule.rule_id or not rule.rule_name:
            raise ValueError("Rule ID and Name must be defined.")

    def _detect_conflicts(self, new_rule_id: str, new_rule: EncryptionRule) -> None:
        for r_id, r in self._by_rule_id.items():
            if r_id != new_rule_id:
                self._check_conflict_between(new_rule_id, new_rule, r_id, r)

    def _check_conflict_between(
        self,
        id1: str,
        rule1: EncryptionRule,
        id2: str,
        rule2: EncryptionRule
    ) -> None:
        EncryptionRuleMatcher.detect_conflicts(rule1, rule2)

    def _sort_key(self, rule: EncryptionRule) -> Any:
        return (-rule.priority, rule.rule_id)

    def register(self, rule_id: str, rule: EncryptionRule) -> None:
        """Registers strategy rules thread-safely and rebuilds indexes."""
        with self._lock:
            if self._frozen:
                raise RegistryFrozenError(f"Registry is frozen. Cannot register rule {rule_id}.", error_code="REGISTRY_FROZEN")
            if rule_id in self._by_rule_id:
                raise RegistryDuplicateError(f"Duplicate rule registered: {rule_id}", error_code="REGISTRY_DUPLICATE")

            # Check overlap conflicts
            self._detect_conflicts(rule_id, rule)

            self._by_rule_id[rule_id] = rule

            # Rebuild multi-indexes
            if rule.recommended_profile:
                prof = rule.recommended_profile
                self._by_algorithm.setdefault(prof.algorithm, []).append(rule)
                self._by_provider.setdefault(prof.key_provider, []).append(rule)
                self._by_key_management_provider.setdefault(prof.key_provider, []).append(rule)

            self._by_dialect.setdefault(rule.target_dialect, []).append(rule)
            if rule.min_version:
                self._by_version.setdefault(rule.min_version, []).append(rule)
            if rule.required_edition:
                self._by_edition.setdefault(rule.required_edition, []).append(rule)

    def list_rules(self) -> List[EncryptionRule]:
        with self._lock:
            return list(self._by_rule_id.values())

    def get_rule(self, rule_id: str) -> Optional[EncryptionRule]:
        with self._lock:
            return self._by_rule_id.get(rule_id)

    def get_rules_for_algorithm(self, algo: EncryptionAlgorithm) -> List[EncryptionRule]:
        with self._lock:
            return list(self._by_algorithm.get(algo, []))

    def get_rules_for_dialect(self, dialect: SystemType) -> List[EncryptionRule]:
        with self._lock:
            return list(self._by_dialect.get(dialect, []))

    def get_rules_for_provider(self, provider: KeyManagementProvider) -> List[EncryptionRule]:
        with self._lock:
            return list(self._by_provider.get(provider, []))

    def get_matching_rules(
        self,
        dialect: SystemType,
        version: str,
        engine: str,
        edition: str
    ) -> List[EncryptionRule]:
        """Runs the rule matcher against the active registry rule set."""
        with self._lock:
            all_rules = list(self._by_rule_id.values())
        return EncryptionRuleMatcher.match_rules(all_rules, dialect, version, engine, edition)

    def snapshot(self) -> "EncryptionStrategyRegistry":
        """Generates a mutable copy-on-write snapshot copy of the registry."""
        with self._lock:
            snap = EncryptionStrategyRegistry(version=self._version)
            for rid, rule in self._by_rule_id.items():
                snap.register(rid, rule)
            return snap

    def hot_reload(self, rules_dict: Dict[str, EncryptionRule]) -> None:
        """Atomic hot swapping swap of rule set within registry locks."""
        with self._lock:
            # Verify no conflicts in the new rules block
            temp_registry = EncryptionStrategyRegistry(version=self._version)
            for rid, rule in rules_dict.items():
                temp_registry.register(rid, rule)

            # Atomically replace local mappings
            self._by_rule_id = temp_registry._by_rule_id
            self._by_algorithm = temp_registry._by_algorithm
            self._by_dialect = temp_registry._by_dialect
            self._by_provider = temp_registry._by_provider
            self._by_version = temp_registry._by_version
            self._by_edition = temp_registry._by_edition
            self._by_key_management_provider = temp_registry._by_key_management_provider
