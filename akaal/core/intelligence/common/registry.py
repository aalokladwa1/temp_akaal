"""
Akaal — Intelligence Extensible Registry Framework
==================================================
Provides the base thread-safe, freeze-compliant, and copy-on-write registry.
"""

import abc
import threading
from typing import Any, Dict, Generic, List, Optional, TypeVar

from akaal.core.intelligence.common.exceptions import (
    ConflictResolutionError,
    RegistryDuplicateError,
    RegistryFrozenError,
)

T = TypeVar("T")


class BaseRegistry(Generic[T], abc.ABC):
    """
    Abstract Base Class for all intelligence and translation registries.
    Supports duplicate check, conflict detection, deterministic sorting,
    freeze state, copy-on-write snapshots, and hot reloading.
    """
    def __init__(self, version: str = "1.0.0") -> None:
        self._rules: Dict[str, T] = {}
        self._frozen: bool = False
        self._lock = threading.RLock()
        self._version: str = version

    @property
    def version(self) -> str:
        return self._version

    @property
    def is_frozen(self) -> bool:
        return self._frozen

    def register(self, rule_id: str, rule: T) -> None:
        """
        Thread-safely registers a rule under the given ID.
        Verifies duplicate IDs and overlaps before finalizing registration.
        """
        # Lock-free check if already frozen to minimize path overhead
        if self._frozen:
            raise RegistryFrozenError(
                f"Cannot register rule '{rule_id}': registry is frozen.",
                error_code="REGISTRY_FROZEN"
            )

        with self._lock:
            # Re-check under lock boundary
            if self._frozen:
                raise RegistryFrozenError(
                    f"Cannot register rule '{rule_id}': registry is frozen.",
                    error_code="REGISTRY_FROZEN"
                )
            if rule_id in self._rules:
                raise RegistryDuplicateError(
                    f"Rule ID '{rule_id}' is already registered in {self.__class__.__name__}.",
                    error_code="REGISTRY_DUPLICATE"
                )
            self._validate_rule(rule)
            self._detect_conflicts(rule_id, rule)
            self._rules[rule_id] = rule

    def get(self, rule_id: str) -> Optional[T]:
        """Looks up a rule directly by its identifier."""
        # Lock-free read path if frozen
        if self._frozen:
            return self._rules.get(rule_id)
        with self._lock:
            return self._rules.get(rule_id)

    def list_rules(self) -> List[T]:
        """Returns all registered rules, sorted deterministically by registry specificity/priority."""
        # Lock-free read path if frozen
        if self._frozen:
            rules_list = list(self._rules.values())
        else:
            with self._lock:
                rules_list = list(self._rules.values())
        return sorted(rules_list, key=self._sort_key)

    def freeze(self) -> None:
        """Transitions the registry to frozen state, disabling further modifications."""
        with self._lock:
            self._frozen = True

    def snapshot(self) -> "BaseRegistry[T]":
        """
        Thread-safely clones the registry to a new, mutable instance.
        Follows the Copy-on-Write (COW) snapshot system.
        """
        with self._lock:
            clone = self.__class__(version=self._version)
            clone._rules = self._rules.copy()
            clone._frozen = False
            return clone

    def hot_reload(self, rules_dict: Dict[str, T]) -> None:
        """
        Loads a new collection of rules atomically.
        Validates the ruleset, verifies duplicates and conflicts, and replaces the live mapping.
        """
        # Create a new candidate mapping to validate isolation
        candidate: Dict[str, T] = {}
        for rule_id, rule in rules_dict.items():
            if rule_id in candidate:
                raise RegistryDuplicateError(
                    f"Rule ID '{rule_id}' duplicated in hot reload dictionary.",
                    error_code="REGISTRY_DUPLICATE_RELOAD"
                )
            self._validate_rule(rule)
            # Detect conflicts against currently building candidate list
            for existing_id, existing_rule in candidate.items():
                self._check_conflict_between(rule_id, rule, existing_id, existing_rule)
            candidate[rule_id] = rule

        # Atomic Swap
        with self._lock:
            if self._frozen:
                raise RegistryFrozenError(
                    "Cannot hot reload a frozen registry.",
                    error_code="REGISTRY_FROZEN_RELOAD"
                )
            self._rules = candidate

    @abc.abstractmethod
    def _validate_rule(self, rule: T) -> None:
        """Performs runtime validation on individual rule parameters."""
        pass

    @abc.abstractmethod
    def _detect_conflicts(self, new_rule_id: str, new_rule: T) -> None:
        """Verifies if the new rule conflicts with any currently registered rule."""
        pass

    @abc.abstractmethod
    def _check_conflict_between(self, id1: str, rule1: T, id2: str, rule2: T) -> None:
        """Asserts whether two rules overlap or contradict each other."""
        pass

    @abc.abstractmethod
    def _sort_key(self, rule: T) -> Any:
        """Returns a deterministic key tuple for priority and tie-breaker sorting."""
        pass
