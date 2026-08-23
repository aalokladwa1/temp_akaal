"""
akaalEngine.schema.authority
============================
Public façade for Authority #4 Schema.
Coordinates discovery fact canonicalization, 28-provider type normalization/emission,
structural mapping, procedural AST transpilation, staged DDL generation, multi-domain DAG sorting,
compatibility/lossiness/risk evaluation, and deterministic SHA-256 provenance fingerprinting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from akaalEngine.discovery.models.snapshot import DiscoverySnapshot
from akaalEngine.schema.assessment.compatibility import (
    CompatibilityBreakdown,
    PreMigrationCompatibilityAssessor,
)
from akaalEngine.schema.assessment.projection import (
    TargetCapacityReport,
    TargetCapacitySchemaProjection,
)
from akaalEngine.schema.assessment.readiness import (
    ReadinessGateReport,
    SchemaReadinessGateProvider,
)
from akaalEngine.schema.assessment.risk import (
    StructuralRiskReport,
    StructuralRiskScorer,
)
from akaalEngine.schema.compat.lifecycle import (
    CompatibilityPackReport,
    CompatibilityRequirementTracker,
)
from akaalEngine.schema.core.memoization import (
    CompiledRuleIndexMemoizationEngine,
    default_memoization_engine,
)
from akaalEngine.schema.core.provenance import DeterministicSchemaProvenanceHasher
from akaalEngine.schema.ddl.emitter import StagedDDLPackage
from akaalEngine.schema.ddl.generator import DDLGenerator
from akaalEngine.schema.dependency.cycle_breaker import CycleBreaker
from akaalEngine.schema.dependency.graph import MultiDomainDependencyGraph
from akaalEngine.schema.dependency.sorter import TopologicalSorter
from akaalEngine.schema.mapping.engine import MappingEngine
from akaalEngine.schema.models.constraints import (
    CanonicalCheckConstraint,
    CanonicalForeignKey,
    CanonicalPrimaryKey,
    CanonicalUniqueConstraint,
)
from akaalEngine.schema.models.indexes import CanonicalIndex, IndexAccessMethod
from akaalEngine.schema.models.mapping import CompiledSchemaMapping
from akaalEngine.schema.models.partitioning import CanonicalPartitioning, PartitionStrategy
from akaalEngine.schema.models.programmables import (
    CanonicalRoutine,
    CanonicalSequence,
    CanonicalUDT,
    RoutineKind,
)
from akaalEngine.schema.models.schema import (
    CanonicalCatalog,
    CanonicalSchema,
    CanonicalSchemaModel,
    CanonicalView,
)
from akaalEngine.schema.models.table import (
    CanonicalColumn,
    CanonicalTable,
    StorageFormat,
    TablePhysicalType,
)
from akaalEngine.schema.models.types import CanonicalType, CanonicalTypeCategory
from akaalEngine.schema.procedural.diagnostics import ProceduralConversionResult
from akaalEngine.schema.procedural.emitters.plpgsql import PLpgSQLEmitter
from akaalEngine.schema.procedural.parsers.plsql import PLSQLParser
from akaalEngine.schema.procedural.parsers.tsql import TSQLParser
from akaalEngine.schema.types.registry import CanonicalTypeRegistry

logger = logging.getLogger("akaalEngine.schema.authority")


@dataclass(frozen=True)
class SchemaCompilationRequest:
    """Request payload for compiling discovery metadata into target schema and DDL artifacts."""
    source_snapshot: Union[DiscoverySnapshot, CanonicalSchemaModel, Mapping[str, Any]]
    target_engine: str
    target_version: Optional[str] = None
    mapping: Optional[CompiledSchemaMapping] = None
    options: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.options, MappingProxyType):
            object.__setattr__(self, "options", MappingProxyType(dict(self.options)))


@dataclass(frozen=True)
class SchemaCompilationResult:
    """Immutable outcome of schema compilation including models, DDL, reports, and provenance."""
    model_id: str
    source_engine: str
    target_engine: str
    canonical_model: CanonicalSchemaModel
    mapped_model: CanonicalSchemaModel
    ddl_package: StagedDDLPackage
    compatibility_report: CompatibilityBreakdown
    risk_report: StructuralRiskReport
    readiness_report: ReadinessGateReport
    capacity_report: TargetCapacityReport
    compatibility_pack_report: CompatibilityPackReport
    procedural_results: Tuple[ProceduralConversionResult, ...]
    topologically_ordered_nodes: Tuple[str, ...]
    provenance_fingerprint: str
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.procedural_results, tuple):
            object.__setattr__(self, "procedural_results", tuple(self.procedural_results))
        if not isinstance(self.topologically_ordered_nodes, tuple):
            object.__setattr__(self, "topologically_ordered_nodes", tuple(self.topologically_ordered_nodes))
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "source_engine": self.source_engine,
            "target_engine": self.target_engine,
            "canonical_model": self.canonical_model.to_dict(),
            "mapped_model": self.mapped_model.to_dict(),
            "ddl_package": self.ddl_package.to_dict(),
            "compatibility_report": self.compatibility_report.to_dict(),
            "risk_report": self.risk_report.to_dict(),
            "readiness_report": self.readiness_report.to_dict(),
            "capacity_report": self.capacity_report.to_dict(),
            "compatibility_pack_report": self.compatibility_pack_report.to_dict(),
            "procedural_results": [r.to_dict() for r in self.procedural_results],
            "topologically_ordered_nodes": list(self.topologically_ordered_nodes),
            "provenance_fingerprint": self.provenance_fingerprint,
            "extra": dict(self.extra),
        }


class SchemaAuthority:
    """
    Public façade for Authority #4 Schema.
    The single canonical authority for schema models, heterogeneous types, DDL generation,
    mapping, procedural AST transpilation, DAG resolution, and migration readiness.
    """

    def __init__(self, memoization_engine: Optional[CompiledRuleIndexMemoizationEngine] = None):
        self._memo = memoization_engine or default_memoization_engine

    async def compile(self, request: SchemaCompilationRequest) -> SchemaCompilationResult:
        """
        Executes the canonical 18-step schema compilation workflow.
        Returns immutable SchemaCompilationResult.
        """
        target_eng = request.target_engine.strip().upper()
        target_ver = request.target_version

        # 1. Canonicalize Discovery Snapshot into CanonicalSchemaModel
        canonical_model = self._canonicalize_input(request.source_snapshot)
        source_eng = canonical_model.source_vendor.upper()

        # 2. Apply Structural Mapping (if provided)
        if request.mapping:
            mapped_model = MappingEngine.apply_mapping(canonical_model, request.mapping, target_vendor=target_eng)
        else:
            mapped_model = canonical_model

        # 3. Assess Datatype Compatibility & Lossiness
        compat_breakdown = PreMigrationCompatibilityAssessor.assess_model(mapped_model, target_eng)

        # 4. Assess Structural Risk
        risk_report = StructuralRiskScorer.score_risk(mapped_model, compat_breakdown)

        # 5. Evaluate Readiness Gate
        readiness_report = SchemaReadinessGateProvider.evaluate_readiness(compat_breakdown, risk_report)

        # 6. Calculate Capacity Projections
        capacity_report = TargetCapacitySchemaProjection.calculate_projection(mapped_model, target_eng)

        # 7. Procedural AST Parsing and Transpilation
        procedural_results = self._transpile_routines(mapped_model, source_eng, target_eng)

        # 8. Staged DDL Generation
        ddl_package = DDLGenerator.generate_ddl_package(mapped_model, target_eng, target_ver)

        # 9. Track Compatibility Helper Requirements
        tracker = CompatibilityRequirementTracker()
        for r in procedural_results:
            for helper in r.required_compat_helpers:
                tracker.record_requirement(helper, r.routine_name, target_eng)
        compat_pack_report = tracker.build_report()

        # 10. Multi-Domain Dependency Graph & Cycle Breaking
        dep_graph = MultiDomainDependencyGraph.build_from_model(mapped_model)
        pruned_graph = CycleBreaker.break_fk_cycles(dep_graph)

        # 11. Topological Sort
        ordered_nodes = TopologicalSorter.sort(pruned_graph)

        # 12. Compute SHA-256 Provenance Fingerprint
        src_hash = DeterministicSchemaProvenanceHasher.compute_model_fingerprint(canonical_model)
        map_hash = DeterministicSchemaProvenanceHasher.compute_mapping_fingerprint(request.mapping) if request.mapping else "NO_MAPPING"
        ddl_hash = DeterministicSchemaProvenanceHasher.compute_ddl_fingerprint(ddl_package)
        provenance = DeterministicSchemaProvenanceHasher.compute_compilation_provenance(
            src_hash, map_hash, ddl_hash, target_eng, target_ver or "default"
        )

        return SchemaCompilationResult(
            model_id=mapped_model.model_id,
            source_engine=source_eng,
            target_engine=target_eng,
            canonical_model=canonical_model,
            mapped_model=mapped_model,
            ddl_package=ddl_package,
            compatibility_report=compat_breakdown,
            risk_report=risk_report,
            readiness_report=readiness_report,
            capacity_report=capacity_report,
            compatibility_pack_report=compat_pack_report,
            procedural_results=tuple(procedural_results),
            topologically_ordered_nodes=tuple(ordered_nodes),
            provenance_fingerprint=provenance,
        )

    def _canonicalize_input(self, src: Union[DiscoverySnapshot, CanonicalSchemaModel, Mapping[str, Any]]) -> CanonicalSchemaModel:
        if isinstance(src, CanonicalSchemaModel):
            return src

        if isinstance(src, DiscoverySnapshot):
            return self._from_discovery_snapshot(src)

        if isinstance(src, Mapping):
            return self._from_dict(src)

        raise TypeError(f"Unsupported source metadata input type: {type(src)}")

    def _from_discovery_snapshot(self, snapshot: DiscoverySnapshot) -> CanonicalSchemaModel:
        identity = snapshot.engine_identity or getattr(snapshot, "identity", None)
        vendor = "GENERIC"
        version = None
        edition = None
        if identity:
            vendor = identity.provider_id or identity.vendor_name
            version = identity.version.raw_version_string if hasattr(identity.version, "raw_version_string") else str(identity.version)
            edition = identity.edition.edition_name if hasattr(identity.edition, "edition_name") else str(identity.edition)

        snap_id = getattr(snapshot, "snapshot_id", None) or getattr(snapshot, "endpoint_id", "ep_default")

        tables: List[CanonicalTable] = []
        for obj_name, facts in snapshot.structures.items():
            # Parse schema and table name
            parts = obj_name.split(".")
            s_name = parts[0] if len(parts) > 1 else "public"
            t_name = parts[-1]

            # Columns
            cols: List[CanonicalColumn] = []
            for col_meta in facts.columns:
                c_name = getattr(col_meta, "name", None) or getattr(col_meta, "column_name", "")
                c_type = getattr(col_meta, "native_type", None) or getattr(col_meta, "data_type", "")
                c_len = getattr(col_meta, "length", None) or getattr(col_meta, "character_maximum_length", None)
                c_prec = getattr(col_meta, "precision", None) or getattr(col_meta, "numeric_precision", None)
                c_scale = getattr(col_meta, "scale", None) or getattr(col_meta, "numeric_scale", None)
                c_null = getattr(col_meta, "nullable", True) if hasattr(col_meta, "nullable") else getattr(col_meta, "is_nullable", True)
                c_def = getattr(col_meta, "default_expression", None) or getattr(col_meta, "column_default", None)
                c_extra = dict(getattr(col_meta, "extra", {}) or getattr(col_meta, "extra_properties", {}))

                ctype = CanonicalTypeRegistry.normalize_source_type(
                    provider=vendor,
                    raw_type=c_type,
                    length=c_len,
                    precision=c_prec,
                    scale=c_scale,
                    extra_metadata=c_extra,
                )
                cols.append(
                    CanonicalColumn(
                        name=c_name,
                        ordinal_position=col_meta.ordinal_position,
                        source_native_type=c_type,
                        canonical_type=ctype,
                        length=c_len,
                        precision=c_prec,
                        scale=c_scale,
                        nullable=c_null,
                        default_expression=c_def,
                        is_identity=col_meta.is_identity,
                        identity_generation=col_meta.identity_generation,
                        comment=col_meta.comment,
                        raw_metadata=c_extra,
                    )
                )

            # Primary Key
            pk = None
            if facts.primary_key:
                pk = CanonicalPrimaryKey(
                    name=facts.primary_key.name,
                    table_name=t_name,
                    schema_name=s_name,
                    columns=facts.primary_key.columns,
                    is_enforced=getattr(facts.primary_key, "is_enforced", True),
                )

            # Foreign Keys
            fks = []
            for fk_facts in facts.foreign_keys:
                fks.append(
                    CanonicalForeignKey(
                        name=fk_facts.name,
                        table_name=t_name,
                        schema_name=s_name,
                        columns=getattr(fk_facts, "columns", None) or getattr(fk_facts, "constrained_columns", ()),
                        referenced_schema=fk_facts.referenced_schema,
                        referenced_table=fk_facts.referenced_table,
                        referenced_columns=fk_facts.referenced_columns,
                        on_update=getattr(fk_facts, "on_update", None) or getattr(fk_facts, "on_update_action", "NO ACTION"),
                        on_delete=getattr(fk_facts, "on_delete", None) or getattr(fk_facts, "on_delete_action", "NO ACTION"),
                        is_deferrable=getattr(fk_facts, "is_deferrable", False),
                        is_initially_deferred=getattr(fk_facts, "is_initially_deferred", False),
                        is_validated=getattr(fk_facts, "is_validated", True),
                    )
                )

            # Unique Constraints
            ucs = []
            for uc_facts in facts.unique_constraints:
                ucs.append(
                    CanonicalUniqueConstraint(
                        name=uc_facts.name,
                        table_name=t_name,
                        schema_name=s_name,
                        columns=uc_facts.columns,
                        is_deferrable=getattr(uc_facts, "is_deferrable", False),
                        nulls_not_distinct=getattr(uc_facts, "nulls_not_distinct", False),
                    )
                )

            # Check Constraints
            cks = []
            for ck_facts in facts.check_constraints:
                cks.append(
                    CanonicalCheckConstraint(
                        name=ck_facts.name,
                        table_name=t_name,
                        schema_name=s_name,
                        check_clause=ck_facts.check_clause,
                        is_enforced=getattr(ck_facts, "is_enforced", True),
                    )
                )

            # Indexes
            idxs = []
            for idx_facts in facts.indexes:
                raw_m = getattr(idx_facts, "access_method", "BTREE")
                if hasattr(raw_m, "value"):
                    raw_m = raw_m.value
                try:
                    access_m = IndexAccessMethod(str(raw_m).upper())
                except (ValueError, AttributeError):
                    access_m = IndexAccessMethod.BTREE

                idxs.append(
                    CanonicalIndex(
                        name=idx_facts.name,
                        table_name=t_name,
                        schema_name=s_name,
                        columns=idx_facts.columns,
                        is_unique=getattr(idx_facts, "is_unique", False),
                        is_primary=getattr(idx_facts, "is_primary", False),
                        access_method=access_m,
                        predicate_expression=getattr(idx_facts, "predicate_expression", None) or getattr(idx_facts, "filter_predicate", None),
                        included_columns=getattr(idx_facts, "included_columns", ()),
                        expression=getattr(idx_facts, "expression", None) or getattr(idx_facts, "expression_definition", None),
                        is_clustered=getattr(idx_facts, "is_clustered", False),
                    )
                )

            # Partitioning
            part_strat = PartitionStrategy.NONE
            facts_part = getattr(facts, "partitioning", None)
            if facts_part and hasattr(facts_part, "strategy"):
                try:
                    strat_val = facts_part.strategy.value if hasattr(facts_part.strategy, "value") else str(facts_part.strategy)
                    part_strat = PartitionStrategy(strat_val.upper())
                except (ValueError, AttributeError):
                    part_strat = PartitionStrategy.NONE

            partitioning = CanonicalPartitioning(
                strategy=part_strat,
                partition_columns=facts_part.partition_columns if facts_part and hasattr(facts_part, "partition_columns") else (),
            )

            tables.append(
                CanonicalTable(
                    table_name=t_name,
                    schema_name=s_name,
                    columns=tuple(cols),
                    primary_key=pk,
                    foreign_keys=tuple(fks),
                    unique_constraints=tuple(ucs),
                    check_constraints=tuple(cks),
                    indexes=tuple(idxs),
                    partitioning=partitioning,
                )
            )

        # Routines
        routines = []
        if snapshot.programmables and snapshot.programmables.routines:
            for r_facts in snapshot.programmables.routines:
                r_type_str = r_facts.routine_type.value if hasattr(r_facts.routine_type, "value") else str(r_facts.routine_type)
                r_kind = RoutineKind.FUNCTION if r_type_str.upper() == "FUNCTION" else RoutineKind.PROCEDURE
                routines.append(
                    CanonicalRoutine(
                        name=r_facts.name,
                        schema_name=r_facts.schema_name,
                        routine_type=r_kind,
                        language=r_facts.language,
                        definition_sql=r_facts.definition_sql,
                    )
                )

        # Sequences
        sequences = []
        if snapshot.programmables and snapshot.programmables.sequences:
            for s_facts in snapshot.programmables.sequences:
                sequences.append(
                    CanonicalSequence(
                        name=s_facts.name,
                        schema_name=s_facts.schema_name,
                        start_value=s_facts.start_value,
                        increment_by=s_facts.increment_by,
                        min_value=s_facts.min_value,
                        max_value=s_facts.max_value,
                        is_cycling=s_facts.is_cycling,
                        current_value=s_facts.current_value,
                        cache_size=getattr(s_facts, "cache_size", 1),
                    )
                )

        # UDTs
        udts = []
        if snapshot.programmables and snapshot.programmables.udts:
            for u_facts in snapshot.programmables.udts:
                udts.append(
                    CanonicalUDT(
                        name=u_facts.name,
                        schema_name=u_facts.schema_name,
                        udt_type=u_facts.udt_type,
                        enum_values=u_facts.enum_values,
                        attributes=u_facts.attributes,
                        underlying_type=u_facts.underlying_type,
                    )
                )

        # Views
        views = []
        views_source = snapshot.objects.views if (snapshot.objects and snapshot.objects.views) else ()
        for v in views_source:
            v_name = getattr(v, "name", str(v))
            v_schema = getattr(v, "schema_name", "public")
            if "." in v_name and v_schema == "public":
                parts = v_name.split(".")
                v_schema = parts[0]
                v_name = parts[-1]
            views.append(CanonicalView(view_name=v_name, schema_name=v_schema))

        unique_schemas = {t.schema_name for t in tables}
        schema_objs = [CanonicalSchema(schema_name=s) for s in unique_schemas]

        return CanonicalSchemaModel(
            model_id=f"model_{snap_id}",
            source_vendor=vendor,
            source_version=version,
            schemas=tuple(schema_objs),
            tables=tuple(tables),
            views=tuple(views),
            routines=tuple(routines),
            sequences=tuple(sequences),
            udts=tuple(udts),
            raw_discovery_facts=snapshot.to_dict(),
        )

    def _from_dict(self, data: Mapping[str, Any]) -> CanonicalSchemaModel:
        return CanonicalSchemaModel(
            model_id=data.get("model_id", "dynamic_model"),
            source_vendor=data.get("source_vendor", "GENERIC"),
            source_version=data.get("source_version"),
            raw_discovery_facts=dict(data),
        )

    def _transpile_routines(
        self,
        model: CanonicalSchemaModel,
        source_engine: str,
        target_engine: str,
    ) -> List[ProceduralConversionResult]:
        results: List[ProceduralConversionResult] = []

        for r in model.routines:
            if not r.definition_sql:
                continue

            try:
                if source_engine == "ORACLE":
                    parser = PLSQLParser(r.definition_sql)
                    ast = parser.parse()
                elif source_engine in ("MSSQL", "SQLSERVER"):
                    parser = TSQLParser(r.definition_sql)
                    ast = parser.parse()
                else:
                    # Fallback PL/SQL parser
                    parser = PLSQLParser(r.definition_sql)
                    ast = parser.parse()

                # Target Procedural SQL Emission
                if target_engine in ("POSTGRESQL", "POSTGRES"):
                    res = PLpgSQLEmitter.emit_routine(ast, schema_name=r.schema_name)
                    results.append(res)
            except Exception as e:
                logger.warning("Procedural transpilation encountered syntax/parsing exception: %s", e)

        return results


# Default singleton Schema authority
default_schema_authority = SchemaAuthority()
