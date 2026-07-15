"""
Akaal — Compression Strategy Registry & Rule Matcher
=====================================================
Implements multi-indexed rules storage, deterministic prioritization,
and strict conflict validation for compression migration strategies.
"""

import threading
from typing import Dict, List, Optional, Tuple, Any

from akaal.core.models.enums import SystemType
from akaal.core.intelligence.common.registry import BaseRegistry
from akaal.core.intelligence.common.exceptions import (
    RegistryFrozenError,
    RegistryDuplicateError,
)
from akaal.core.intelligence.compression_aware.exceptions import CompressionRegistryConflictError
from akaal.core.intelligence.compression_aware.models import (
    CompressionRule,
    CompressionAlgorithm,
)


class CompressionRuleMatcher:
    """Deterministic matcher responsible for prioritizing and filtering compression rules."""

    @staticmethod
    def calculate_specificity(rule: CompressionRule, version: str, engine: str, edition: str) -> int:
        """Calculates specificity score for a matching rule."""
        score = 0
        
        # Version specificity
        if rule.min_version:
            if rule.min_version == version:
                score += 10
            else:
                score += 5
                
        # Engine specificity
        if rule.required_engine:
            if rule.required_engine.upper() == engine.upper():
                score += 5
                
        # Edition specificity
        if rule.required_edition:
            if rule.required_edition.upper() == edition.upper():
                score += 5
                
        return score

    @staticmethod
    def matches(rule: CompressionRule, dialect: SystemType, version: str, engine: str, edition: str) -> bool:
        """Evaluates if a rule matches target dialect, version, engine, and edition parameters."""
        if rule.target_dialect != dialect:
            return False

        # Version ranges check
        if rule.min_version:
            try:
                # Compare versions hierarchically
                if CompressionRuleMatcher._parse_version(version) < CompressionRuleMatcher._parse_version(rule.min_version):
                    return False
            except Exception:
                if version < rule.min_version:
                    return False

        if rule.max_version:
            try:
                if CompressionRuleMatcher._parse_version(version) > CompressionRuleMatcher._parse_version(rule.max_version):
                    return False
            except Exception:
                if version > rule.max_version:
                    return False

        # Engine check
        if rule.required_engine and engine:
            if rule.required_engine.upper() != engine.upper():
                return False

        # Edition check
        if rule.required_edition and edition:
            if rule.required_edition.upper() != edition.upper():
                return False

        return True

    @staticmethod
    def _parse_version(version_str: str) -> Tuple[int, ...]:
        """Parses version strings to integer tuple for robust comparisons."""
        clean = "".join(c if c.isdigit() or c == "." else "" for c in version_str)
        return tuple(int(x) for x in clean.split(".") if x)

    @classmethod
    def match_rules(
        cls,
        rules: List[CompressionRule],
        dialect: SystemType,
        version: str,
        engine: str,
        edition: str
    ) -> List[CompressionRule]:
        """Filters rules, matches constraints, and resolves priorities deterministically."""
        matched = []
        for rule in rules:
            if cls.matches(rule, dialect, version, engine, edition):
                matched.append(rule)

        # Stable sort sorting keys:
        # 1. Specificity (descending)
        # 2. Priority (descending)
        # 3. Rule ID (alphabetical ascending tie-breaker)
        def sort_key(r: CompressionRule) -> Any:
            spec = cls.calculate_specificity(r, version, engine, edition)
            return (-spec, -r.priority, r.rule_id)

        matched.sort(key=sort_key)
        return matched

    @classmethod
    def detect_conflicts(cls, rule1: CompressionRule, rule2: CompressionRule) -> None:
        """Audits overlap bounds to verify absence of contradictory strategy results."""
        if rule1.target_dialect != rule2.target_dialect:
            return

        # Check engine overlap
        engine_overlap = True
        if rule1.required_engine and rule2.required_engine:
            engine_overlap = rule1.required_engine.upper() == rule2.required_engine.upper()

        # Check edition overlap
        edition_overlap = True
        if rule1.required_edition and rule2.required_edition:
            edition_overlap = rule1.required_edition.upper() == rule2.required_edition.upper()

        if engine_overlap and edition_overlap:
            # Overlap in versions
            ver_overlap = True
            if rule1.max_version and rule2.min_version:
                if rule1.max_version < rule2.min_version:
                    ver_overlap = False
            if rule2.max_version and rule1.min_version:
                if rule2.max_version < rule1.min_version:
                    ver_overlap = False

            if ver_overlap and rule1.priority == rule2.priority:
                raise CompressionRegistryConflictError(
                    f"Conflict detected between '{rule1.rule_id}' and '{rule2.rule_id}': "
                    f"Overlapping constraints with matching priority {rule1.priority}.",
                    error_code="COMPRESSION_RULE_CONFLICT"
                )


class CompressionStrategyRegistry(BaseRegistry[CompressionRule]):
    """Reentrant rules registry with multi-index lookup tables for strategy lookups."""

    def __init__(self, version: str = "1.0.0") -> None:
        super().__init__(version=version)
        self._lock = threading.RLock()
        
        # Multi-indexes
        self._by_rule_id: Dict[str, CompressionRule] = {}
        self._by_algorithm: Dict[CompressionAlgorithm, List[CompressionRule]] = {}
        self._by_dialect: Dict[SystemType, List[CompressionRule]] = {}
        self._by_version: Dict[str, List[CompressionRule]] = {}
        self._by_engine: Dict[str, List[CompressionRule]] = {}

    def _validate_rule(self, rule: CompressionRule) -> None:
        if not rule.rule_id or not rule.rule_name:
            raise ValueError("Rule ID and Name must be defined.")

    def _detect_conflicts(self, new_rule_id: str, new_rule: CompressionRule) -> None:
        for r_id, r in self._by_rule_id.items():
            if r_id != new_rule_id:
                self._check_conflict_between(new_rule_id, new_rule, r_id, r)

    def _check_conflict_between(
        self,
        id1: str,
        rule1: CompressionRule,
        id2: str,
        rule2: CompressionRule
    ) -> None:
        CompressionRuleMatcher.detect_conflicts(rule1, rule2)

    def _sort_key(self, rule: CompressionRule) -> Any:
        return (-rule.priority, rule.rule_id)

    def register(self, rule_id: str, rule: CompressionRule) -> None:
        """Registers a rule and rebuilds multi-indexes thread-safely."""
        with self._lock:
            if self._frozen:
                raise RegistryFrozenError(f"Registry is frozen. Cannot register rule {rule_id}.", error_code="REGISTRY_FROZEN")
            if rule_id in self._by_rule_id:
                raise RegistryDuplicateError(f"Duplicate rule registered: {rule_id}", error_code="REGISTRY_DUPLICATE")
            
            # Conflict detection checks
            for existing_rule in self._by_rule_id.values():
                CompressionRuleMatcher.detect_conflicts(rule, existing_rule)

            self._by_rule_id[rule_id] = rule
            
            # Update indexes
            self._by_algorithm.setdefault(rule.recommended_profile.algorithm, []).append(rule)
            self._by_dialect.setdefault(rule.target_dialect, []).append(rule)
            
            if rule.min_version:
                self._by_version.setdefault(rule.min_version, []).append(rule)
            if rule.required_engine:
                self._by_engine.setdefault(rule.required_engine.upper(), []).append(rule)

    def freeze(self) -> None:
        """Freezes registry to allow lock-free reads."""
        with self._lock:
            self._frozen = True

    def snapshot(self) -> "CompressionStrategyRegistry":
        """Creates a mutable copy-on-write snapshot clone."""
        with self._lock:
            snap = CompressionStrategyRegistry(version=self._version)
            for rule_id, rule in self._by_rule_id.items():
                snap.register(rule_id, rule)
            return snap

    def get(self, rule_id: str) -> Optional[CompressionRule]:
        """Fetches rule by identifier."""
        if self._frozen:
            return self._by_rule_id.get(rule_id)
        with self._lock:
            return self._by_rule_id.get(rule_id)

    def list_rules(self) -> List[CompressionRule]:
        """Lists registered strategy rules."""
        if self._frozen:
            return list(self._by_rule_id.values())
        with self._lock:
            return list(self._by_rule_id.values())

    def get_rules_for_dialect(self, dialect: SystemType) -> List[CompressionRule]:
        """Index-based rule retrieval for a target dialect."""
        if self._frozen:
            return self._by_dialect.get(dialect, [])
        with self._lock:
            return self._by_dialect.get(dialect, [])

    def get_rules_for_algorithm(self, algo: CompressionAlgorithm) -> List[CompressionRule]:
        """Index-based rule retrieval for a recommended algorithm."""
        if self._frozen:
            return self._by_algorithm.get(algo, [])
        with self._lock:
            return self._by_algorithm.get(algo, [])

    def get_rules_for_engine(self, engine: str) -> List[CompressionRule]:
        """Index-based rule retrieval for a storage engine."""
        key = engine.upper()
        if self._frozen:
            return self._by_engine.get(key, [])
        with self._lock:
            return self._by_engine.get(key, [])

    def get_matching_rules(
        self,
        dialect: SystemType,
        version: str,
        engine: str,
        edition: str
    ) -> List[CompressionRule]:
        """Resolves ordered, prioritized matching rules for target context."""
        # Multi-index retrieval: get all rules for dialect
        candidates = self.get_rules_for_dialect(dialect)
        return CompressionRuleMatcher.match_rules(candidates, dialect, version, engine, edition)
