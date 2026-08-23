"""
akaalEngine.extensions.spi.authority_contract
============================================
Defines the specifications for Engine Authority SPI contracts.
Allows each Engine Authority to register its contract, expected strategy protocol/base class, and validation rules.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Sequence, Type

from akaalEngine.extensions.errors.taxonomy import AuthorityContractMismatchError
from akaalEngine.extensions.models.compatibility import CompatibilityRange
from akaalEngine.extensions.models.identity import AuthorityId


@dataclass(frozen=True)
class AuthorityContractDefinition:
    """
    Contract specification for an Engine Authority.
    Defines what an authority requires from strategy contributions claiming to implement it.
    """
    authority_id: AuthorityId
    contract_version: str
    description: str
    expected_base_type: Optional[Type[Any]] = None
    validator: Optional[Callable[[Any], bool]] = None
    known_capabilities: Sequence[str] = field(default_factory=tuple)
    compatibility_range: CompatibilityRange = field(default_factory=lambda: CompatibilityRange("*"))

    def validate_strategy_instance(self, instance: Any) -> bool:
        """Validates that a concrete strategy instance conforms to this authority's contract."""
        if instance is None:
            raise AuthorityContractMismatchError(
                f"Strategy instance is None for authority '{self.authority_id}'."
            )
        if self.expected_base_type is not None:
            if not isinstance(instance, self.expected_base_type):
                raise AuthorityContractMismatchError(
                    f"Strategy instance {type(instance).__name__} does not inherit from expected base {self.expected_base_type.__name__} for authority '{self.authority_id}'."
                )
        if self.validator is not None:
            try:
                ok = self.validator(instance)
                if not ok:
                    raise AuthorityContractMismatchError(
                        f"Strategy instance {type(instance).__name__} failed custom contract validation for authority '{self.authority_id}'."
                    )
            except Exception as exc:
                if isinstance(exc, AuthorityContractMismatchError):
                    raise
                raise AuthorityContractMismatchError(
                    f"Contract validation error for authority '{self.authority_id}': {exc}"
                )
        return True


class AuthorityContractRegistry:
    """
    Thread-safe registry of all known Engine Authority contracts.
    """
    _instance: Optional[AuthorityContractRegistry] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._contracts: dict[AuthorityId, AuthorityContractDefinition] = {}

    @classmethod
    def get_instance(cls) -> AuthorityContractRegistry:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    def register_contract(self, contract: AuthorityContractDefinition) -> None:
        with self._lock:
            self._contracts[contract.authority_id] = contract

    def get_contract(self, authority_id: AuthorityId) -> Optional[AuthorityContractDefinition]:
        with self._lock:
            return self._contracts.get(authority_id)

    def list_contracts(self) -> Sequence[AuthorityContractDefinition]:
        with self._lock:
            return tuple(self._contracts.values())

    def has_contract(self, authority_id: AuthorityId) -> bool:
        with self._lock:
            return authority_id in self._contracts


default_contract_registry = AuthorityContractRegistry.get_instance()
