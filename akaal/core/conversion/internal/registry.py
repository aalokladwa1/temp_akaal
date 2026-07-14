"""
Akaal — Type Conversion Registry
================================
Implements the pre-compiled, Copy-on-Write, thread-safe rules registry with startup validation.
"""

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set
from akaal.core.conversion.api.models import DataType, DbVersion, ConversionContext
from akaal.core.conversion.internal.rules import ConversionRule
from akaal.core.conversion.exceptions import RegistryError

class IRuleRegistry(ABC):
    """Interface governing the rule lookup contract."""
    
    @abstractmethod
    def lookup(self, source: DataType, context: ConversionContext) -> Tuple[ConversionRule, ...]:
        """Looks up matching rules sorted descending by specificity."""
        pass


@dataclass(frozen=True)
class RegistrySnapshot:
    """An immutable precompiled snapshot of rules optimized for lock-free reads."""
    rules: Tuple[ConversionRule, ...]
    index: Dict[Tuple[str, str, str], Tuple[ConversionRule, ...]]  # (source_vendor, target_vendor, category) -> Rules

    def query(self, source: DataType, context: ConversionContext) -> Tuple[ConversionRule, ...]:
        key = (context.source_vendor.upper(), context.target_vendor.upper(), source.category.value)
        candidates = self.index.get(key, ())
        
        # Filter and sort matching rules dynamically
        matches = [r for r in candidates if r.matches(source, context)]
        return tuple(sorted(matches, key=lambda r: r.specificity_score, reverse=True))


class ThreadSafeRuleRegistry(IRuleRegistry):
    """
    Registry executing a Copy-on-Write snapshot replacement model.
    Read requests run lock-free. Write/Registration triggers lock, validates, compiles, and swaps snapshot.
    """

    def __init__(self):
        self._write_lock = threading.Lock()
        self._active_snapshot = RegistrySnapshot(rules=(), index={})

    def lookup(self, source: DataType, context: ConversionContext) -> Tuple[ConversionRule, ...]:
        # Lock-free lookup
        return self._active_snapshot.query(source, context)

    def register(self, rule: ConversionRule) -> None:
        """Registers a rule, runs validation assertions, compiles index, and swaps active snapshot."""
        with self._write_lock:
            # 1. Check duplicate IDs
            for existing in self._active_snapshot.rules:
                if existing.metadata.rule_id == rule.metadata.rule_id:
                    raise RegistryError(f"Duplicate rule ID registration attempt: '{rule.metadata.rule_id}'")

            # 2. Add rule
            new_rules = self._active_snapshot.rules + (rule,)

            # 3. Perform registry self-validation assertions
            self._validate_rules(new_rules)

            # 4. Compile pre-indexed structures
            self._active_snapshot = self._compile(new_rules)

    def register_multiple(self, rules: List[ConversionRule]) -> None:
        """Helper to register multiple rules in a single atomic transaction."""
        with self._write_lock:
            # Duplicate ID validation in batch
            registered_ids = {r.metadata.rule_id for r in self._active_snapshot.rules}
            for rule in rules:
                if rule.metadata.rule_id in registered_ids:
                    raise RegistryError(f"Duplicate rule ID registration attempt: '{rule.metadata.rule_id}'")
                registered_ids.add(rule.metadata.rule_id)

            new_rules = self._active_snapshot.rules + tuple(rules)
            self._validate_rules(new_rules)
            self._active_snapshot = self._compile(new_rules)

    def clear(self) -> None:
        """Purges all rules and clears snapshot indexes."""
        with self._write_lock:
            self._active_snapshot = RegistrySnapshot(rules=(), index={})

    def _validate_rules(self, rules: Tuple[ConversionRule, ...]) -> None:
        """Performs validation for overlapping rule definitions and specificity conflicts."""
        # Check rule conflicts within same source-to-target paths
        for i, r1 in enumerate(rules):
            for r2 in rules[i + 1:]:
                # If they target different vendor pairs, no conflict is possible
                if r1.metadata.vendor_scope != r2.metadata.vendor_scope:
                    continue

                # Check if they overlap on specificity score and target mapping characteristics
                # DeclarativeConversionRule exposes matches/specificity metrics
                from akaal.core.conversion.internal.rules import DeclarativeConversionRule
                if isinstance(r1, DeclarativeConversionRule) and isinstance(r2, DeclarativeConversionRule):
                    # Check category overlap
                    if r1._match_category != r2._match_category:
                        continue
                    
                    # Check if matching type names intersect (empty list matches all types of that category)
                    names_intersect = (
                        not r1._match_names or not r2._match_names or
                        bool(r1._match_names.intersection(r2._match_names))
                    )
                    if not names_intersect:
                        continue

                    # Check version overlap
                    version_overlap = (
                        r1._min_source_version <= r2._max_source_version and
                        r2._min_source_version <= r1._max_source_version
                    )
                    if version_overlap:
                        # Ambiguity check: Same specificity score under identical match targets
                        if r1.specificity_score == r2.specificity_score:
                            raise RegistryError(
                                f"Ambiguous overlapping rule priority detected between '{r1.metadata.rule_id}' "
                                f"and '{r2.metadata.rule_id}' (specificity score: {r1.specificity_score})."
                            )

    def _compile(self, rules: Tuple[ConversionRule, ...]) -> RegistrySnapshot:
        """Pre-compiles rules into a lookup directory indexed by vendor scope and category."""
        index: Dict[Tuple[str, str, str], List[ConversionRule]] = {}
        for rule in rules:
            src_vendor, tgt_vendor = rule.metadata.vendor_scope
            # Lookup categories from source match settings
            from akaal.core.conversion.internal.rules import DeclarativeConversionRule
            if isinstance(rule, DeclarativeConversionRule):
                category_key = rule._match_category.value
                key = (src_vendor.upper(), tgt_vendor.upper(), category_key)
                if key not in index:
                    index[key] = []
                index[key].append(rule)
        
        # Convert lists to immutable tuples
        frozen_index = {k: tuple(v) for k, v in index.items()}
        return RegistrySnapshot(rules=rules, index=frozen_index)
