"""
akaalEngine.extensions.models.identity
======================================
Immutable, normalized identity types for extensions, providers, strategies, authorities, and registry generations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


_VALID_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_\-\.]{0,127}$")


def normalize_identifier(val: str, field_name: str = "identifier") -> str:
    """Normalizes an identifier to lowercase stripped string and validates format."""
    if not val or not isinstance(val, str):
        raise ValueError(f"{field_name} must be a non-empty string.")
    normalized = val.strip().lower()
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty or whitespace.")
    if not _VALID_IDENTIFIER_PATTERN.match(normalized):
        raise ValueError(
            f"Invalid {field_name} '{normalized}'. Must match ^[a-z0-9][a-z0-9_\\-\\.]{{0,127}}$"
        )
    return normalized


@dataclass(frozen=True, order=True)
class ExtensionId:
    """Canonical identifier for an extension package or bundle."""
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", normalize_identifier(self.value, "ExtensionId"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, order=True)
class ProviderId:
    """Canonical identifier for a data provider (e.g. 'postgresql', 'snowflake', 's3')."""
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", normalize_identifier(self.value, "ProviderId"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, order=True)
class AuthorityId:
    """Canonical identifier for an Engine authority (e.g. 'connection', 'discovery', 'schema', 'transport', 'change_capture')."""
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", normalize_identifier(self.value, "AuthorityId"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, order=True)
class StrategyId:
    """Canonical identifier for an authority-specific strategy implementation (e.g. 'postgres-pgcopy', 'oracle-logminer')."""
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", normalize_identifier(self.value, "StrategyId"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, order=True)
class RegistryGeneration:
    """Monotonically increasing sequence tracking published immutable registry states."""
    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or self.value < 1:
            raise ValueError(f"RegistryGeneration must be a positive integer >= 1, got {self.value}.")

    def next(self) -> RegistryGeneration:
        return RegistryGeneration(self.value + 1)

    def __str__(self) -> str:
        return str(self.value)
