"""
akaalEngine.discovery.models.sampling
====================================
Bounded deterministic preview sampling and document shape inference models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class SampledFieldObservation:
    """Statistical observations on a field within a bounded sample set."""
    field_name: str
    observed_types: Tuple[str, ...]
    null_count: int = 0
    sample_count: int = 0
    min_value_repr: Optional[str] = None
    max_value_repr: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.observed_types, tuple):
            object.__setattr__(self, "observed_types", tuple(self.observed_types))

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "observed_types": list(self.observed_types),
            "null_count": self.null_count,
            "sample_count": self.sample_count,
            "min_value_repr": self.min_value_repr,
            "max_value_repr": self.max_value_repr,
        }


@dataclass(frozen=True)
class InferredDocumentShape:
    """Inferred schema shape for non-relational or schema-less document collections."""
    collection_name: str
    schema_name: str = "default"
    fields: Tuple[SampledFieldObservation, ...] = field(default_factory=tuple)
    is_polymorphic: bool = False
    sample_size: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.fields, tuple):
            object.__setattr__(self, "fields", tuple(self.fields))

    def to_dict(self) -> dict[str, Any]:
        return {
            "collection_name": self.collection_name,
            "schema_name": self.schema_name,
            "fields": [f.to_dict() for f in self.fields],
            "is_polymorphic": self.is_polymorphic,
            "sample_size": self.sample_size,
        }


@dataclass(frozen=True)
class SampledRecordSet:
    """
    Bounded, redacted sample records for Mapping Studio and UI preview.
    Explicitly marked is_sampled=True and carries sensitive data redaction flag.
    """
    table_name: str
    schema_name: str = "public"
    column_names: Tuple[str, ...] = field(default_factory=tuple)
    records: Tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    sample_count: int = 0
    execution_duration_ms: float = 0.0
    is_sampled: bool = True
    is_redacted: bool = True
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.column_names, tuple):
            object.__setattr__(self, "column_names", tuple(self.column_names))
        if not isinstance(self.records, tuple):
            # Wrap rows in MappingProxyType
            proxies = tuple(
                MappingProxyType(dict(r)) if not isinstance(r, MappingProxyType) else r
                for r in self.records
            )
            object.__setattr__(self, "records", proxies)
        if not self.sample_count:
            object.__setattr__(self, "sample_count", len(self.records))

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "column_names": list(self.column_names),
            "records": [dict(r) for r in self.records],
            "sample_count": self.sample_count,
            "execution_duration_ms": self.execution_duration_ms,
            "is_sampled": self.is_sampled,
            "is_redacted": self.is_redacted,
            "error_message": self.error_message,
        }

