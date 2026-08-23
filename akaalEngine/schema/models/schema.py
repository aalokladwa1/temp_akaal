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

    def compute_schema_fingerprint(self) -> str:
        """Computes deterministic fingerprint for CanonicalSchemaModel."""
        from akaalEngine.schema.core.provenance import DeterministicSchemaProvenanceHasher
        return DeterministicSchemaProvenanceHasher.compute_model_fingerprint(self)

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

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CanonicalSchemaModel:
        """Losslessly reconstructs a CanonicalSchemaModel from dictionary form."""
        from akaalEngine.schema.models.constraints import (
            CanonicalCheckConstraint,
            CanonicalForeignKey,
            CanonicalPrimaryKey,
            CanonicalUniqueConstraint,
        )
        from akaalEngine.schema.models.indexes import CanonicalIndex, IndexAccessMethod
        from akaalEngine.schema.models.partitioning import CanonicalPartitioning, PartitionStrategy
        from akaalEngine.schema.models.programmables import (
            CanonicalRoutineParameter,
            ParameterMode,
            RoutineKind,
        )
        from akaalEngine.schema.models.table import CanonicalColumn
        from akaalEngine.schema.models.types import CanonicalType, CanonicalTypeCategory

        # 1. Catalogs & Schemas
        catalogs = []
        for cd in data.get("catalogs", []):
            cat_schemas = [CanonicalSchema(schema_name=s.get("schema_name", ""), catalog_name=s.get("catalog_name"), comment=s.get("comment"), extra=s.get("extra", {})) for s in cd.get("schemas", [])]
            catalogs.append(CanonicalCatalog(catalog_name=cd.get("catalog_name", ""), schemas=tuple(cat_schemas), comment=cd.get("comment"), extra=cd.get("extra", {})))

        schemas = [CanonicalSchema(schema_name=s.get("schema_name", ""), catalog_name=s.get("catalog_name"), comment=s.get("comment"), extra=s.get("extra", {})) for s in data.get("schemas", [])]

        # 2. Tables
        tables = []
        for td in data.get("tables", []):
            cols = []
            for col_d in td.get("columns", []):
                ct_d = col_d.get("canonical_type") or {}
                ct_cat_raw = ct_d.get("category", "UNKNOWN")
                try:
                    ct_cat = CanonicalTypeCategory(ct_cat_raw)
                except ValueError:
                    ct_cat = CanonicalTypeCategory.UNKNOWN

                ctype = CanonicalType(
                    category=ct_cat,
                    raw_vendor_type=ct_d.get("raw_vendor_type", col_d.get("source_native_type", "VARCHAR")),
                    precision=ct_d.get("precision", col_d.get("precision")),
                    scale=ct_d.get("scale", col_d.get("scale")),
                    length=ct_d.get("length", col_d.get("length")),
                    bits=ct_d.get("bits"),
                    is_signed=ct_d.get("is_signed", True),
                    is_timezone_aware=ct_d.get("is_timezone_aware", ct_d.get("timezone_aware", False)),
                    dimensions=ct_d.get("dimensions"),
                    srid=ct_d.get("srid"),
                )
                cols.append(
                    CanonicalColumn(
                        name=col_d.get("name", ""),
                        ordinal_position=col_d.get("ordinal_position", 1),
                        source_native_type=col_d.get("source_native_type", "VARCHAR"),
                        canonical_type=ctype,
                        length=col_d.get("length"),
                        precision=col_d.get("precision"),
                        scale=col_d.get("scale"),
                        byte_semantics=col_d.get("byte_semantics", False),
                        nullable=col_d.get("nullable", True),
                        default_expression=col_d.get("default_expression"),
                        is_identity=col_d.get("is_identity", False),
                        identity_generation=col_d.get("identity_generation"),
                        is_computed=col_d.get("is_computed", False),
                        computed_expression=col_d.get("computed_expression"),
                        is_lob=col_d.get("is_lob", False),
                        is_array=col_d.get("is_array", False),
                        array_element_type=col_d.get("array_element_type"),
                        comment=col_d.get("comment"),
                        raw_metadata=col_d.get("raw_metadata", {}),
                        extra=col_d.get("extra", {}),
                    )
                )

            # PK
            pk = None
            pk_d = td.get("primary_key")
            if pk_d:
                pk = CanonicalPrimaryKey(
                    name=pk_d.get("name", "pk"),
                    table_name=pk_d.get("table_name", td.get("table_name", "")),
                    schema_name=pk_d.get("schema_name", td.get("schema_name", "")),
                    columns=tuple(pk_d.get("columns", ())),
                    is_enforced=pk_d.get("is_enforced", True),
                    extra=pk_d.get("extra", {}),
                )

            # FKs
            fks = []
            for fkd in td.get("foreign_keys", []):
                fks.append(
                    CanonicalForeignKey(
                        name=fkd.get("name", "fk"),
                        table_name=fkd.get("table_name", td.get("table_name", "")),
                        schema_name=fkd.get("schema_name", td.get("schema_name", "")),
                        columns=tuple(fkd.get("columns", ())),
                        referenced_schema=fkd.get("referenced_schema", ""),
                        referenced_table=fkd.get("referenced_table", ""),
                        referenced_columns=tuple(fkd.get("referenced_columns", ())),
                        on_update=fkd.get("on_update", "NO ACTION"),
                        on_delete=fkd.get("on_delete", "NO ACTION"),
                        is_deferrable=fkd.get("is_deferrable", False),
                        is_initially_deferred=fkd.get("is_initially_deferred", False),
                        is_validated=fkd.get("is_validated", True),
                        is_enforced=fkd.get("is_enforced", True),
                        extra=fkd.get("extra", {}),
                    )
                )

            # UCs
            ucs = []
            for ucd in td.get("unique_constraints", []):
                ucs.append(
                    CanonicalUniqueConstraint(
                        name=ucd.get("name", "uc"),
                        table_name=ucd.get("table_name", td.get("table_name", "")),
                        schema_name=ucd.get("schema_name", td.get("schema_name", "")),
                        columns=tuple(ucd.get("columns", ())),
                        is_deferrable=ucd.get("is_deferrable", False),
                        nulls_not_distinct=ucd.get("nulls_not_distinct", False),
                        is_enforced=ucd.get("is_enforced", True),
                        extra=ucd.get("extra", {}),
                    )
                )

            # CKs
            cks = []
            for ckd in td.get("check_constraints", []):
                cks.append(
                    CanonicalCheckConstraint(
                        name=ckd.get("name", "ck"),
                        table_name=ckd.get("table_name", td.get("table_name", "")),
                        schema_name=ckd.get("schema_name", td.get("schema_name", "")),
                        check_clause=ckd.get("check_clause", ""),
                        is_enforced=ckd.get("is_enforced", True),
                        is_not_null=ckd.get("is_not_null", False),
                        not_null_column=ckd.get("not_null_column"),
                        extra=ckd.get("extra", {}),
                    )
                )

            # Indexes
            idxs = []
            for idxd in td.get("indexes", []):
                raw_am = idxd.get("access_method", "BTREE")
                try:
                    am = IndexAccessMethod(str(raw_am).upper())
                except ValueError:
                    am = IndexAccessMethod.UNKNOWN
                idxs.append(
                    CanonicalIndex(
                        name=idxd.get("name", "idx"),
                        table_name=idxd.get("table_name", td.get("table_name", "")),
                        schema_name=idxd.get("schema_name", td.get("schema_name", "")),
                        columns=tuple(idxd.get("columns", ())),
                        is_unique=idxd.get("is_unique", False),
                        is_primary=idxd.get("is_primary", False),
                        access_method=am,
                        predicate_expression=idxd.get("predicate_expression"),
                        included_columns=tuple(idxd.get("included_columns", ())),
                        expression=idxd.get("expression"),
                        is_clustered=idxd.get("is_clustered", False),
                        vector_dimensions=idxd.get("vector_dimensions"),
                        distance_metric=idxd.get("distance_metric"),
                        extra=idxd.get("extra", {}),
                    )
                )

            # Partitioning
            part_d = td.get("partitioning") or {}
            raw_strat = part_d.get("strategy", "NONE")
            try:
                strat = PartitionStrategy(str(raw_strat).upper())
            except ValueError:
                strat = PartitionStrategy.UNKNOWN
            part = CanonicalPartitioning(
                strategy=strat,
                partition_columns=tuple(part_d.get("partition_columns", ())),
                subpartition_strategy=part_d.get("subpartition_strategy"),
                subpartition_columns=tuple(part_d.get("subpartition_columns", ())),
                partitions=part_d.get("partitions", ()),
                subpartitions=part_d.get("subpartitions", ()),
                token_ranges=part_d.get("token_ranges", ()),
                shard_key_columns=tuple(part_d.get("shard_key_columns", ())),
                distribution_style=part_d.get("distribution_style"),
                extra=part_d.get("extra", {}),
            )

            tables.append(
                CanonicalTable(
                    table_name=td.get("table_name", ""),
                    schema_name=td.get("schema_name", ""),
                    catalog_name=td.get("catalog_name"),
                    table_type=td.get("table_type", "BASE_TABLE"),
                    storage_format=td.get("storage_format"),
                    columns=tuple(cols),
                    primary_key=pk,
                    foreign_keys=tuple(fks),
                    unique_constraints=tuple(ucs),
                    check_constraints=tuple(cks),
                    indexes=tuple(idxs),
                    partitioning=part,
                    row_format=td.get("row_format"),
                    compression=td.get("compression"),
                    tablespace=td.get("tablespace"),
                    comment=td.get("comment"),
                    raw_source_properties=td.get("raw_source_properties", {}),
                    extra=td.get("extra", {}),
                )
            )

        # 3. Views
        views = [
            CanonicalView(
                view_name=vd.get("view_name", ""),
                schema_name=vd.get("schema_name", ""),
                catalog_name=vd.get("catalog_name"),
                view_definition=vd.get("view_definition") or vd.get("definition_sql"),
                definition_sql=vd.get("view_definition") or vd.get("definition_sql"),
                is_materialized=vd.get("is_materialized", False),
                materialized_refresh_mode=vd.get("materialized_refresh_mode"),
                check_option=vd.get("check_option"),
                is_read_only=vd.get("is_read_only", False),
                columns=tuple(vd.get("columns", ())),
                dependencies=tuple(vd.get("dependencies", ())),
                comment=vd.get("comment"),
                extra=vd.get("extra", {}),
            )
            for vd in data.get("views", [])
        ]

        # 4. Routines
        routines = []
        for rd in data.get("routines", []):
            raw_rk = rd.get("routine_type", "PROCEDURE")
            try:
                rk = RoutineKind(str(raw_rk).upper())
            except ValueError:
                rk = RoutineKind.PROCEDURE

            params = []
            for pd in rd.get("parameters", []):
                raw_pm = pd.get("mode", "IN")
                try:
                    pm = ParameterMode(str(raw_pm).upper())
                except ValueError:
                    pm = ParameterMode.IN
                params.append(
                    CanonicalRoutineParameter(
                        name=pd.get("name", ""),
                        data_type=pd.get("data_type", "VARCHAR"),
                        mode=pm,
                        ordinal_position=pd.get("ordinal_position", 1),
                        default_value=pd.get("default_value"),
                    )
                )

            routines.append(
                CanonicalRoutine(
                    name=rd.get("name", ""),
                    schema_name=rd.get("schema_name", ""),
                    routine_type=rk,
                    language=rd.get("language", "SQL"),
                    definition_sql=rd.get("definition_sql", ""),
                    parameters=tuple(params),
                    return_type=rd.get("return_type"),
                    is_deterministic=rd.get("is_deterministic", False),
                    security_type=rd.get("security_type", "DEFINER"),
                    dependencies=tuple(rd.get("dependencies", ())),
                    extra=rd.get("extra", {}),
                )
            )

        # 5. Packages
        packages = [
            CanonicalPackage(
                name=pd.get("name", ""),
                schema_name=pd.get("schema_name", ""),
                spec_sql=pd.get("spec_sql"),
                body_sql=pd.get("body_sql"),
                public_routines=tuple([CanonicalRoutine(name=r.get("name", ""), schema_name=pd.get("schema_name", ""), definition_sql=r.get("definition_sql", "")) for r in pd.get("public_routines", pd.get("routines", []))]),
                extra=pd.get("extra", {}),
            )
            for pd in data.get("packages", [])
        ]

        # 6. Triggers
        from akaalEngine.schema.models.programmables import TriggerTiming
        triggers = []
        for trd in data.get("triggers", []):
            raw_tt = trd.get("timing", trd.get("trigger_timing", "AFTER"))
            try:
                tt = TriggerTiming(str(raw_tt).upper())
            except ValueError:
                tt = TriggerTiming.AFTER

            raw_ev = trd.get("events")
            if not raw_ev and "trigger_event" in trd:
                raw_ev = (trd["trigger_event"],)
            elif not raw_ev:
                raw_ev = ("INSERT",)

            triggers.append(
                CanonicalTrigger(
                    name=trd.get("name", ""),
                    table_name=trd.get("table_name", ""),
                    schema_name=trd.get("schema_name", ""),
                    timing=tt,
                    events=tuple(raw_ev),
                    definition_sql=trd.get("definition_sql", ""),
                    when_clause=trd.get("when_clause"),
                    is_enabled=not trd.get("is_disabled", False) if "is_disabled" in trd else trd.get("is_enabled", True),
                    extra=trd.get("extra", {}),
                )
            )

        # 7. Sequences
        sequences = [
            CanonicalSequence(
                name=sqd.get("name", ""),
                schema_name=sqd.get("schema_name", ""),
                start_value=sqd.get("start_value", 1),
                increment_by=sqd.get("increment_by", 1),
                min_value=sqd.get("min_value"),
                max_value=sqd.get("max_value"),
                is_cycling=sqd.get("is_cycling", False),
                current_value=sqd.get("current_value"),
                cache_size=sqd.get("cache_size", 1),
                extra=sqd.get("extra", {}),
            )
            for sqd in data.get("sequences", [])
        ]

        # 8. UDTs
        udts = []
        for ud in data.get("udts", []):
            udts.append(
                CanonicalUDT(
                    name=ud.get("name", ""),
                    schema_name=ud.get("schema_name", ""),
                    udt_type=str(ud.get("udt_type", "ENUM")).upper(),
                    underlying_type=ud.get("underlying_type"),
                    enum_values=tuple(ud.get("enum_values", ())),
                    attributes=ud.get("attributes", {}),
                    base_check_clause=ud.get("base_check_clause"),
                    extra=ud.get("extra", {}),
                )
            )

        # 9. Synonyms
        synonyms = [
            CanonicalSynonym(
                synonym_name=synd.get("synonym_name", ""),
                schema_name=synd.get("schema_name", ""),
                target_object_name=synd.get("target_object_name", ""),
                target_schema_name=synd.get("target_schema_name", ""),
                target_catalog_name=synd.get("target_catalog_name"),
                is_public=synd.get("is_public", False),
                extra=synd.get("extra", {}),
            )
            for synd in data.get("synonyms", [])
        ]

        return cls(
            model_id=data.get("model_id", "dict_model"),
            source_vendor=data.get("source_vendor", "GENERIC"),
            source_version=data.get("source_version"),
            catalogs=tuple(catalogs),
            schemas=tuple(schemas),
            tables=tuple(tables),
            views=tuple(views),
            routines=tuple(routines),
            packages=tuple(packages),
            triggers=tuple(triggers),
            sequences=tuple(sequences),
            udts=tuple(udts),
            synonyms=tuple(synonyms),
            raw_discovery_facts=data.get("raw_discovery_facts", {}),
            extra=data.get("extra", {}),
        )
