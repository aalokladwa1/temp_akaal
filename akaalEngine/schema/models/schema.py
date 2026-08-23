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
from akaalEngine.schema.models.types import freeze_deep


@dataclass(frozen=True)
class CanonicalView:
    """Canonical database view or materialized view."""
    view_name: str
    schema_name: str = "public"
    catalog_name: Optional[str] = None
    view_definition: Optional[str] = None
    definition_sql: Optional[str] = None
    is_materialized: bool = False
    materialized_refresh_mode: Optional[str] = None
    check_option: Optional[str] = None
    is_read_only: bool = False
    columns: Tuple[str, ...] = field(default_factory=tuple)
    dependencies: Tuple[str, ...] = field(default_factory=tuple)
    comment: Optional[str] = None
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if self.view_definition is None and self.definition_sql is not None:
            object.__setattr__(self, "view_definition", self.definition_sql)
        elif self.definition_sql is None and self.view_definition is not None:
            object.__setattr__(self, "definition_sql", self.view_definition)
        if not isinstance(self.columns, tuple):
            object.__setattr__(self, "columns", tuple(self.columns))
        if not isinstance(self.dependencies, tuple):
            object.__setattr__(self, "dependencies", tuple(self.dependencies))
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    @property
    def qualified_name(self) -> str:
        if self.schema_name:
            return f"{self.schema_name}.{self.view_name}"
        return self.view_name

    def to_dict(self) -> dict[str, Any]:
        return {
            "view_name": self.view_name,
            "schema_name": self.schema_name,
            "catalog_name": self.catalog_name,
            "view_definition": self.view_definition,
            "definition_sql": self.view_definition,
            "is_materialized": self.is_materialized,
            "materialized_refresh_mode": self.materialized_refresh_mode,
            "check_option": self.check_option,
            "is_read_only": self.is_read_only,
            "columns": list(self.columns),
            "dependencies": list(self.dependencies),
            "comment": self.comment,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class CanonicalSynonym:
    """Canonical synonym or alias."""
    synonym_name: str
    target_object_name: str
    schema_name: str = "public"
    target_schema_name: Optional[str] = None
    target_catalog_name: Optional[str] = None
    is_public: bool = False
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    @property
    def qualified_name(self) -> str:
        if self.schema_name:
            return f"{self.schema_name}.{self.synonym_name}"
        return self.synonym_name

    @property
    def target_object(self) -> str:
        return self.target_object_name

    @property
    def target_schema(self) -> str:
        return self.target_schema_name or "public"

    def to_dict(self) -> dict[str, Any]:
        return {
            "synonym_name": self.synonym_name,
            "target_object_name": self.target_object_name,
            "schema_name": self.schema_name,
            "target_schema_name": self.target_schema_name,
            "target_catalog_name": self.target_catalog_name,
            "is_public": self.is_public,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class CanonicalSchema:
    """Canonical database schema namespace container."""
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
        object.__setattr__(self, "extra", freeze_deep(self.extra))

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
        object.__setattr__(self, "extra", freeze_deep(self.extra))

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
        object.__setattr__(self, "raw_discovery_facts", freeze_deep(self.raw_discovery_facts))
        object.__setattr__(self, "extra", freeze_deep(self.extra))

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
