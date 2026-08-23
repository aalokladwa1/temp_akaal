"""
akaalEngine.schema.models.schema
================================
Canonical Schema Model, Catalogs, Schemas, Views, and Synonyms.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from akaalEngine.schema.models.programmables import (
    CanonicalPackage,
    CanonicalRoutine,
    CanonicalSequence,
    CanonicalTrigger,
    CanonicalUDT,
)
from akaalEngine.schema.models.table import CanonicalTable


@dataclass(frozen=True)
class CanonicalView:
    """Canonical SQL View or Materialized View."""
    view_name: str
    schema_name: str = "public"
    definition_sql: str = ""
    dependencies: Tuple[str, ...] = field(default_factory=tuple)
    is_materialized: bool = False
    refresh_mode: Optional[str] = None  # e.g. "COMPLETE", "FAST", "DEMAND"
    comment: Optional[str] = None
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.dependencies, tuple):
            object.__setattr__(self, "dependencies", tuple(self.dependencies))
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    @property
    def qualified_name(self) -> str:
        return f"{self.schema_name}.{self.view_name}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "view_name": self.view_name,
            "schema_name": self.schema_name,
            "definition_sql": self.definition_sql,
            "dependencies": list(self.dependencies),
            "is_materialized": self.is_materialized,
            "refresh_mode": self.refresh_mode,
            "comment": self.comment,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class CanonicalSynonym:
    """Canonical Synonym / Alias."""
    synonym_name: str
    schema_name: str = "public"
    target_catalog: Optional[str] = None
    target_schema: str = "public"
    target_object: str = ""
    is_public: bool = False
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    @property
    def qualified_name(self) -> str:
        return f"{self.schema_name}.{self.synonym_name}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "synonym_name": self.synonym_name,
            "schema_name": self.schema_name,
            "target_catalog": self.target_catalog,
            "target_schema": self.target_schema,
            "target_object": self.target_object,
            "is_public": self.is_public,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class CanonicalSchema:
    """Canonical database schema / namespace container."""
    schema_name: str
    catalog_name: Optional[str] = None
    tables: Tuple[CanonicalTable, ...] = field(default_factory=tuple)
    views: Tuple[CanonicalView, ...] = field(default_factory=tuple)
    routines: Tuple[CanonicalRoutine, ...] = field(default_factory=tuple)
    packages: Tuple[CanonicalPackage, ...] = field(default_factory=tuple)
    triggers: Tuple[CanonicalTrigger, ...] = field(default_factory=tuple)
    sequences: Tuple[CanonicalSequence, ...] = field(default_factory=tuple)
    udts: Tuple[CanonicalUDT, ...] = field(default_factory=tuple)
    synonyms: Tuple[CanonicalSynonym, ...] = field(default_factory=tuple)
    comment: Optional[str] = None
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        for attr in ("tables", "views", "routines", "packages", "triggers", "sequences", "udts", "synonyms"):
            val = getattr(self, attr)
            if not isinstance(val, tuple):
                object.__setattr__(self, attr, tuple(val))
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_name": self.schema_name,
            "catalog_name": self.catalog_name,
            "tables": [t.to_dict() for t in self.tables],
            "views": [v.to_dict() for v in self.views],
            "routines": [r.to_dict() for r in self.routines],
            "packages": [p.to_dict() for p in self.packages],
            "triggers": [tr.to_dict() for tr in self.triggers],
            "sequences": [s.to_dict() for s in self.sequences],
            "udts": [u.to_dict() for u in self.udts],
            "synonyms": [syn.to_dict() for syn in self.synonyms],
            "comment": self.comment,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class CanonicalCatalog:
    """Canonical database catalog / database container."""
    catalog_name: str
    schemas: Tuple[CanonicalSchema, ...] = field(default_factory=tuple)
    comment: Optional[str] = None
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.schemas, tuple):
            object.__setattr__(self, "schemas", tuple(self.schemas))
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "catalog_name": self.catalog_name,
            "schemas": [s.to_dict() for s in self.schemas],
            "comment": self.comment,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class CanonicalSchemaModel:
    """
    Top-level Canonical Schema Model (IR).
    Represents the complete normalized schema estate with lossless raw discovery facts.
    """
    model_id: str
    source_vendor: str
    source_version: Optional[str] = None
    catalogs: Tuple[CanonicalCatalog, ...] = field(default_factory=tuple)
    schemas: Tuple[CanonicalSchema, ...] = field(default_factory=tuple)
    tables: Tuple[CanonicalTable, ...] = field(default_factory=tuple)
    views: Tuple[CanonicalView, ...] = field(default_factory=tuple)
    routines: Tuple[CanonicalRoutine, ...] = field(default_factory=tuple)
    packages: Tuple[CanonicalPackage, ...] = field(default_factory=tuple)
    triggers: Tuple[CanonicalTrigger, ...] = field(default_factory=tuple)
    sequences: Tuple[CanonicalSequence, ...] = field(default_factory=tuple)
    udts: Tuple[CanonicalUDT, ...] = field(default_factory=tuple)
    synonyms: Tuple[CanonicalSynonym, ...] = field(default_factory=tuple)
    raw_discovery_facts: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        for attr in ("catalogs", "schemas", "tables", "views", "routines", "packages", "triggers", "sequences", "udts", "synonyms"):
            val = getattr(self, attr)
            if not isinstance(val, tuple):
                object.__setattr__(self, attr, tuple(val))
        if not isinstance(self.raw_discovery_facts, MappingProxyType):
            object.__setattr__(self, "raw_discovery_facts", MappingProxyType(dict(self.raw_discovery_facts)))
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    def get_table(self, schema_name: str, table_name: str) -> Optional[CanonicalTable]:
        s_lower = schema_name.lower()
        t_lower = table_name.lower()
        for tbl in self.tables:
            if tbl.schema_name.lower() == s_lower and tbl.table_name.lower() == t_lower:
                return tbl
        return None

    def get_view(self, schema_name: str, view_name: str) -> Optional[CanonicalView]:
        s_lower = schema_name.lower()
        v_lower = view_name.lower()
        for v in self.views:
            if v.schema_name.lower() == s_lower and v.view_name.lower() == v_lower:
                return v
        return None

    def get_routine(self, schema_name: str, routine_name: str) -> Optional[CanonicalRoutine]:
        s_lower = schema_name.lower()
        r_lower = routine_name.lower()
        for r in self.routines:
            if r.schema_name.lower() == s_lower and r.name.lower() == r_lower:
                return r
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "source_vendor": self.source_vendor,
            "source_version": self.source_version,
            "catalogs": [c.to_dict() for c in self.catalogs],
            "schemas": [s.to_dict() for s in self.schemas],
            "tables": [t.to_dict() for t in self.tables],
            "views": [v.to_dict() for v in self.views],
            "routines": [r.to_dict() for r in self.routines],
            "packages": [p.to_dict() for p in self.packages],
            "triggers": [tr.to_dict() for tr in self.triggers],
            "sequences": [seq.to_dict() for seq in self.sequences],
            "udts": [u.to_dict() for u in self.udts],
            "synonyms": [syn.to_dict() for syn in self.synonyms],
            "raw_discovery_facts": dict(self.raw_discovery_facts),
            "extra": dict(self.extra),
        }
