"""
akaalEngine.discovery.models.programmables
=========================================
Stored procedures, functions, packages, triggers, sequences, and UDT fact models.
Captures lossless physical source code and metadata required by procedural AST transpilation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple


class RoutineType(str, Enum):
    """Types of executable database routines."""
    PROCEDURE = "PROCEDURE"
    FUNCTION = "FUNCTION"
    PACKAGE_SPEC = "PACKAGE_SPEC"
    PACKAGE_BODY = "PACKAGE_BODY"
    AGGREGATE = "AGGREGATE"
    WINDOW = "WINDOW"


class TriggerTiming(str, Enum):
    """Database trigger execution timings."""
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    INSTEAD_OF = "INSTEAD_OF"


@dataclass(frozen=True)
class RoutineParameterFacts:
    """Discovered routine parameter definition."""
    name: str
    data_type: str
    mode: str = "IN"  # "IN", "OUT", "INOUT", "VARIADIC"
    ordinal_position: int = 1
    default_value: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "data_type": self.data_type,
            "mode": self.mode,
            "ordinal_position": self.ordinal_position,
            "default_value": self.default_value,
        }


@dataclass(frozen=True)
class RoutineFacts:
    """Discovered stored procedure, function, package, or UDF facts."""
    name: str
    schema_name: str = "public"
    routine_type: RoutineType = RoutineType.PROCEDURE
    language: str = "SQL"
    parameters: Tuple[RoutineParameterFacts, ...] = field(default_factory=tuple)
    return_type: Optional[str] = None
    definition_sql: Optional[str] = None
    package_name: Optional[str] = None
    security_type: Optional[str] = None  # "DEFINER", "INVOKER"
    is_deterministic: bool = False
    volatility: Optional[str] = None     # "IMMUTABLE", "STABLE", "VOLATILE"
    parallel_safety: Optional[str] = None
    dependencies: Tuple[str, ...] = field(default_factory=tuple)
    properties: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.parameters, tuple):
            object.__setattr__(self, "parameters", tuple(self.parameters))
        if not isinstance(self.dependencies, tuple):
            object.__setattr__(self, "dependencies", tuple(self.dependencies))
        if not isinstance(self.properties, MappingProxyType):
            object.__setattr__(self, "properties", MappingProxyType(dict(self.properties)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "schema_name": self.schema_name,
            "routine_type": self.routine_type.value,
            "language": self.language,
            "parameters": [p.to_dict() for p in self.parameters],
            "return_type": self.return_type,
            "definition_sql": self.definition_sql,
            "package_name": self.package_name,
            "security_type": self.security_type,
            "is_deterministic": self.is_deterministic,
            "volatility": self.volatility,
            "parallel_safety": self.parallel_safety,
            "dependencies": list(self.dependencies),
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class TriggerFacts:
    """Discovered database trigger facts."""
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

    def __post_init__(self) -> None:
        if not isinstance(self.events, tuple):
            object.__setattr__(self, "events", tuple(self.events))

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
        }


@dataclass(frozen=True)
class SequenceFacts:
    """Discovered independent sequence facts."""
    name: str
    schema_name: str = "public"
    start_value: int = 1
    increment_by: int = 1
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    is_cycling: bool = False
    current_value: Optional[int] = None

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
        }


@dataclass(frozen=True)
class UDTFacts:
    """Discovered user-defined type or enum facts."""
    name: str
    schema_name: str = "public"
    udt_type: str = "ENUM"  # "ENUM", "COMPOSITE", "DOMAIN", "DISTINCT"
    enum_values: Tuple[str, ...] = field(default_factory=tuple)
    attributes: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    underlying_type: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.enum_values, tuple):
            object.__setattr__(self, "enum_values", tuple(self.enum_values))
        if not isinstance(self.attributes, MappingProxyType):
            object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "schema_name": self.schema_name,
            "udt_type": self.udt_type,
            "enum_values": list(self.enum_values),
            "attributes": dict(self.attributes),
            "underlying_type": self.underlying_type,
        }


@dataclass(frozen=True)
class ProgrammableInventory:
    """Complete inventory of programmable business logic objects."""
    routines: Tuple[RoutineFacts, ...] = field(default_factory=tuple)
    triggers: Tuple[TriggerFacts, ...] = field(default_factory=tuple)
    sequences: Tuple[SequenceFacts, ...] = field(default_factory=tuple)
    udts: Tuple[UDTFacts, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for attr in ("routines", "triggers", "sequences", "udts"):
            val = getattr(self, attr)
            if not isinstance(val, tuple):
                object.__setattr__(self, attr, tuple(val))

    def to_dict(self) -> dict[str, Any]:
        return {
            "routines": [r.to_dict() for r in self.routines],
            "triggers": [t.to_dict() for t in self.triggers],
            "sequences": [s.to_dict() for s in self.sequences],
            "udts": [u.to_dict() for u in self.udts],
        }
