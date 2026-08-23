"""
akaalEngine.schema.models.programmables
=======================================
Stored procedures, functions, packages, triggers, sequences, and UDT semantic models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple

from akaalEngine.schema.models.types import CanonicalType, freeze_deep


class RoutineKind(str, Enum):
    """Types of executable database routines."""
    PROCEDURE = "PROCEDURE"
    FUNCTION = "FUNCTION"
    PACKAGE_SPEC = "PACKAGE_SPEC"
    PACKAGE_BODY = "PACKAGE_BODY"
    AGGREGATE = "AGGREGATE"
    WINDOW = "WINDOW"


class ParameterMode(str, Enum):
    """Parameter passing modes."""
    IN = "IN"
    OUT = "OUT"
    INOUT = "INOUT"
    VARIADIC = "VARIADIC"


class TriggerTiming(str, Enum):
    """Database trigger execution timings."""
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    INSTEAD_OF = "INSTEAD_OF"


@dataclass(frozen=True)
class CanonicalRoutineParameter:
    """Discovered or normalized routine parameter."""
    name: str
    data_type: str
    canonical_type: Optional[CanonicalType] = None
    mode: ParameterMode = ParameterMode.IN
    ordinal_position: int = 1
    default_value: Optional[str] = None
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "data_type": self.data_type,
            "canonical_type": self.canonical_type.to_dict() if self.canonical_type else None,
            "mode": self.mode.value,
            "ordinal_position": self.ordinal_position,
            "default_value": self.default_value,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class CanonicalRoutine:
    """Canonical Stored Procedure or Function definition."""
    name: str
    schema_name: str = "public"
    routine_type: RoutineKind = RoutineKind.PROCEDURE
    language: str = "SQL"
    parameters: Tuple[CanonicalRoutineParameter, ...] = field(default_factory=tuple)
    return_type: Optional[str] = None
    return_canonical_type: Optional[CanonicalType] = None
    definition_sql: Optional[str] = None
    package_name: Optional[str] = None
    security_type: Optional[str] = None  # "DEFINER", "INVOKER"
    is_deterministic: bool = False
    volatility: Optional[str] = None     # "IMMUTABLE", "STABLE", "VOLATILE"
    parallel_safety: Optional[str] = None
    dependencies: Tuple[str, ...] = field(default_factory=tuple)
    properties: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.parameters, tuple):
            object.__setattr__(self, "parameters", tuple(self.parameters))
        if not isinstance(self.dependencies, tuple):
            object.__setattr__(self, "dependencies", tuple(self.dependencies))
        object.__setattr__(self, "properties", freeze_deep(self.properties))
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    @property
    def qualified_name(self) -> str:
        if self.package_name:
            return f"{self.schema_name}.{self.package_name}.{self.name}"
        return f"{self.schema_name}.{self.name}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "schema_name": self.schema_name,
            "routine_type": self.routine_type.value,
            "language": self.language,
            "parameters": [p.to_dict() for p in self.parameters],
            "return_type": self.return_type,
            "return_canonical_type": self.return_canonical_type.to_dict() if self.return_canonical_type else None,
            "definition_sql": self.definition_sql,
            "package_name": self.package_name,
            "security_type": self.security_type,
            "is_deterministic": self.is_deterministic,
            "volatility": self.volatility,
            "parallel_safety": self.parallel_safety,
            "dependencies": list(self.dependencies),
            "properties": dict(self.properties),
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class CanonicalPackage:
    """Canonical Oracle or DB2 Package container with spec and body."""
    name: str
    schema_name: str = "public"
    spec_sql: Optional[str] = None
    body_sql: Optional[str] = None
    public_routines: Tuple[CanonicalRoutine, ...] = field(default_factory=tuple)
    private_routines: Tuple[CanonicalRoutine, ...] = field(default_factory=tuple)
    state_variables: Tuple[Tuple[str, str], ...] = field(default_factory=tuple)  # (name, type)
    dependencies: Tuple[str, ...] = field(default_factory=tuple)
    properties: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        for attr in ("public_routines", "private_routines", "state_variables", "dependencies"):
            val = getattr(self, attr)
            if not isinstance(val, tuple):
                object.__setattr__(self, attr, tuple(val))
        object.__setattr__(self, "properties", freeze_deep(self.properties))
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    @property
    def qualified_name(self) -> str:
        return f"{self.schema_name}.{self.name}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "schema_name": self.schema_name,
            "spec_sql": self.spec_sql,
            "body_sql": self.body_sql,
            "public_routines": [r.to_dict() for r in self.public_routines],
            "private_routines": [r.to_dict() for r in self.private_routines],
            "state_variables": [list(sv) for sv in self.state_variables],
            "dependencies": list(self.dependencies),
            "properties": dict(self.properties),
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class CanonicalTrigger:
    """Canonical Trigger definition."""
    name: str
    table_name: str
    schema_name: str = "public"
    timing: TriggerTiming = TriggerTiming.BEFORE
    events: Tuple[str, ...] = field(default_factory=lambda: ("INSERT",))
    definition_sql: Optional[str] = None
    is_enabled: bool = True
    action_orientation: str = "ROW"  # "ROW" or "STATEMENT"
    when_clause: Optional[str] = None
    order_weight: Optional[int] = None
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.events, tuple):
            object.__setattr__(self, "events", tuple(self.events))
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    @property
    def qualified_name(self) -> str:
        return f"{self.schema_name}.{self.name}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "timing": self.timing.value,
            "events": list(self.events),
            "definition_sql": self.definition_sql,
            "is_enabled": self.is_enabled,
            "action_orientation": self.action_orientation,
            "when_clause": self.when_clause,
            "order_weight": self.order_weight,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class CanonicalSequence:
    """Canonical Sequence definition."""
    name: str
    schema_name: str = "public"
    start_value: int = 1
    increment_by: int = 1
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    is_cycling: bool = False
    current_value: Optional[int] = None
    cache_size: int = 1
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    @property
    def qualified_name(self) -> str:
        return f"{self.schema_name}.{self.name}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "schema_name": self.schema_name,
            "start_value": self.start_value,
            "increment_by": self.increment_by,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "is_cycling": self.is_cycling,
            "current_value": self.current_value,
            "cache_size": self.cache_size,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class CanonicalUDT:
    """Canonical User-Defined Type (UDT), Enum, Domain, or Composite type."""
    name: str
    schema_name: str = "public"
    udt_type: str = "ENUM"  # "ENUM", "COMPOSITE", "DOMAIN", "DISTINCT"
    enum_values: Tuple[str, ...] = field(default_factory=tuple)
    attributes: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))  # name -> native type
    underlying_type: Optional[str] = None
    base_check_clause: Optional[str] = None
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.enum_values, tuple):
            object.__setattr__(self, "enum_values", tuple(self.enum_values))
        object.__setattr__(self, "attributes", freeze_deep(self.attributes))
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    @property
    def qualified_name(self) -> str:
        return f"{self.schema_name}.{self.name}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "schema_name": self.schema_name,
            "udt_type": self.udt_type,
            "enum_values": list(self.enum_values),
            "attributes": dict(self.attributes),
            "underlying_type": self.underlying_type,
            "base_check_clause": self.base_check_clause,
            "extra": dict(self.extra),
        }
