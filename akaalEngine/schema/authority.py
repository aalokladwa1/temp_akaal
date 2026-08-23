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
from akaalEngine.schema.core.provenance import (
    DeterministicSchemaProvenanceHasher,
    get_rule_implementation_version,
)
from akaalEngine.schema.ddl.emitter import StagedDDLPackage
from akaalEngine.schema.ddl.generator import DDLGenerator
from akaalEngine.schema.dependency.cycle_breaker import CycleBreaker
from akaalEngine.schema.dependency.graph import MultiDomainDependencyGraph
from akaalEngine.schema.dependency.sorter import TopologicalSorter
from akaalEngine.schema.mapping.engine import MappingEngine
from akaalEngine.schema.dialect import (
    DateTimeDialectTranslator,
    FunctionDialectTranslator,
    SequenceDialectTranslator,
)
from akaalEngine.schema.models.constraints import (
    CanonicalCheckConstraint,
    CanonicalExclusionConstraint,
    CanonicalForeignKey,
    CanonicalPrimaryKey,
    CanonicalUniqueConstraint,
)
from akaalEngine.schema.models.indexes import CanonicalIndex, IndexAccessMethod
from akaalEngine.schema.models.mapping import CompiledSchemaMapping
from akaalEngine.schema.models.partitioning import CanonicalPartitioning, PartitionStrategy
from akaalEngine.schema.models.programmables import (
    CanonicalPackage,
    CanonicalRoutine,
    CanonicalSequence,
    CanonicalTrigger,
    CanonicalUDT,
    RoutineKind,
)
from akaalEngine.schema.models.schema import (
    CanonicalCatalog,
    CanonicalSchema,
    CanonicalSchemaModel,
    CanonicalSynonym,
    CanonicalView,
)
from akaalEngine.schema.models.table import (
    CanonicalColumn,
    CanonicalTable,
    StorageFormat,
    TablePhysicalType,
)
from akaalEngine.schema.models.types import CanonicalType, CanonicalTypeCategory, freeze_deep
from akaalEngine.schema.procedural.diagnostics import (
    ConversionState,
    ProceduralConversionResult,
    ProceduralDiagnostic,
)
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
        object.__setattr__(self, "options", freeze_deep(self.options))


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
        object.__setattr__(self, "extra", freeze_deep(self.extra))

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
        with CanonicalTypeRegistry.scoped_memoization_engine(self._memo):
            # Stage 1: Request Pre-Validation & Parameter Normalization
            if not request.target_engine or not request.target_engine.strip():
                raise ValueError("Schema compilation request must specify a valid target_engine.")
            target_eng = request.target_engine.strip().upper()
            target_ver = request.target_version

            # Stage 2: Lossless Input Canonicalization
            canonical_model = self._canonicalize_input(request.source_snapshot)
            source_eng = canonical_model.source_vendor.upper()

            # Stage 3: Structural Mapping & Schema Routing
            if request.mapping:
                mapped_model = MappingEngine.apply_mapping(canonical_model, request.mapping, target_vendor=target_eng)
            else:
                mapped_model = canonical_model

            # Stage 4: Token-Aware SQL Dialect Translation (defaults, checks, view queries)
            mapped_model = self._apply_dialect_translations(mapped_model, source_eng, target_eng)

            # Stage 5: Heterogeneous Type Normalization (Memoized in registry)
            # Stage 6: Target Type Emission & Safety Evaluation (Memoized in registry)
            # Stage 7: Lossiness & Truncation Reason-Code Evaluation (17 reason codes)
            # Stage 8: Pre-Migration Compatibility Breakdown Calculation
            compat_breakdown = PreMigrationCompatibilityAssessor.assess_model(mapped_model, target_eng)

            # Stage 9: Structural Risk & Complexity Scoring
            risk_report = StructuralRiskScorer.score_risk(mapped_model, compat_breakdown)

            # Stage 10: Governance Readiness Gate Evaluation
            readiness_report = SchemaReadinessGateProvider.evaluate_readiness(compat_breakdown, risk_report)

            # Stage 11: Truthful Storage Capacity & Compression Projection
            capacity_report = TargetCapacitySchemaProjection.calculate_projection(mapped_model, target_eng)

            # Stage 12: Procedural AST Parsing & Transpilation (Memoized)
            procedural_results = self._transpile_routines(mapped_model, source_eng, target_eng)

            # Stage 13: Procedural Verification & Zero-Leakage DDL Guard
            procedural_ddl_artifacts: List[StructuredDDLArtifact] = []
            emitter = DDLGenerator.get_emitter(target_eng, target_ver)
            for r in mapped_model.routines:
                matching_res = next((res for res in procedural_results if res.routine_name == r.name), None)
                conv_state = matching_res.conversion_state.value if matching_res else None
                is_valid_conv = matching_res and matching_res.conversion_state in (
                    ConversionState.TRANSPILED,
                    ConversionState.CONVERTED,
                    ConversionState.SYNTACTICALLY_CHECKED,
                    ConversionState.COMPATIBILITY_WRAPPED,
                )
                converted_sql = matching_res.emitted_sql if is_valid_conv else None
                procedural_ddl_artifacts.extend(
                    emitter.emit_routine_artifacts(
                        r,
                        converted_sql=converted_sql,
                        conversion_state=conv_state,
                        source_engine=source_eng,
                    )
                )
            for tr in mapped_model.triggers:
                procedural_ddl_artifacts.extend(emitter.emit_trigger_artifacts(tr, source_engine=source_eng))

            # Stage 14: Compatibility Pack Lifecycle Requirement Tracking
            tracker = CompatibilityRequirementTracker()
            for r in procedural_results:
                for helper in r.required_compat_helpers:
                    tracker.record_requirement(helper, r.routine_name, target_eng)
            compat_pack_report = tracker.build_report()

            # Stage 15: Multi-Domain Dependency DAG Construction
            dep_graph = MultiDomainDependencyGraph.build(mapped_model)

            # Stage 16: Circular Foreign Key Cycle Breaking
            pruned_graph = CycleBreaker.break_fk_cycles(dep_graph)

            # Stage 17: Deterministic Topological Sorting (Kahn + Tarjan SCC)
            ordered_nodes = TopologicalSorter.sort(pruned_graph)

            # Stage 18: Staged Multi-Pass DDL Generation & Composite SHA-256 Fingerprinting
            use_chunked = request.options.get("chunked_compilation", False) or len(mapped_model.tables) > request.options.get("chunk_size", 500)
            if use_chunked:
                from akaalEngine.schema.core.processor import LargeEstateChunkedSchemaProcessor
                ddl_package = LargeEstateChunkedSchemaProcessor.compile_large_estate_package(
                    mapped_model,
                    target_eng,
                    target_ver,
                    chunk_size=request.options.get("chunk_size", 500),
                    procedural_artifacts=procedural_ddl_artifacts,
                )
            else:
                ddl_package = DDLGenerator.generate_ddl_package(
                    mapped_model,
                    target_eng,
                    target_ver,
                    procedural_artifacts=procedural_ddl_artifacts,
                )

            # Full 18-stage composite provenance fingerprint
            src_hash = DeterministicSchemaProvenanceHasher.compute_model_fingerprint(canonical_model)
            map_hash = DeterministicSchemaProvenanceHasher.compute_mapping_fingerprint(request.mapping) if request.mapping else "NO_MAPPING"
            ddl_hash = DeterministicSchemaProvenanceHasher.compute_ddl_fingerprint(ddl_package)
            proc_hash = DeterministicSchemaProvenanceHasher.hash_dict({"results": [r.to_dict() for r in procedural_results]})
            read_hash = DeterministicSchemaProvenanceHasher.hash_dict(readiness_report.to_dict())
            compat_breakdown_hash = DeterministicSchemaProvenanceHasher.hash_dict(compat_breakdown.to_dict())
            compat_pack_hash = DeterministicSchemaProvenanceHasher.hash_dict(compat_pack_report.to_dict())
            risk_hash = DeterministicSchemaProvenanceHasher.hash_dict(risk_report.to_dict())
            capacity_hash = DeterministicSchemaProvenanceHasher.hash_dict(capacity_report.to_dict())
            opts_hash = DeterministicSchemaProvenanceHasher.hash_dict(dict(request.options))

            provenance = DeterministicSchemaProvenanceHasher.compute_compilation_provenance(
                source_model_hash=src_hash,
                mapping_hash=map_hash,
                ddl_package_hash=ddl_hash,
                target_engine=target_eng,
                target_version=target_ver or "default",
                rule_set_version=str(self._memo.rule_generation),
                procedural_hash=proc_hash,
                readiness_hash=read_hash,
                compatibility_breakdown_hash=compat_breakdown_hash,
                compat_pack_hash=compat_pack_hash,
                risk_hash=risk_hash,
                capacity_hash=capacity_hash,
                options_hash=opts_hash,
                rule_impl_version=get_rule_implementation_version(),
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

    def stream_compile(
        self,
        request: SchemaCompilationRequest,
        chunk_size: int = 500,
    ) -> Iterator[StagedDDLPackage]:
        """
        Executes memory-bounded streaming compilation for large enterprise estates (SCH-069).
        Streams DDL packages chunk by chunk without materializing all artifacts into memory simultaneously.
        """
        with CanonicalTypeRegistry.scoped_memoization_engine(self._memo):
            target_eng = request.target_engine.strip().upper()
            target_ver = request.target_version

            from akaalEngine.schema.core.processor import LargeEstateChunkedSchemaProcessor

            if hasattr(request.source_snapshot, "__iter__") and not isinstance(request.source_snapshot, (CanonicalSchemaModel, dict, DiscoverySnapshot)):
                # Pure lazy table stream
                yield from LargeEstateChunkedSchemaProcessor.stream_compile_estate(
                    tables_stream=request.source_snapshot,
                    target_engine=target_eng,
                    target_version=target_ver,
                    chunk_size=chunk_size,
                    mapping=request.mapping,
                    on_summary=request.options.get("on_summary"),
                )
                return

            canonical_model = self._canonicalize_input(request.source_snapshot)
            source_eng = canonical_model.source_vendor.upper()

            yield from LargeEstateChunkedSchemaProcessor.stream_compile_estate(
                tables_stream=canonical_model.tables,
                target_engine=target_eng,
                target_version=target_ver,
                chunk_size=chunk_size,
                source_vendor=source_eng,
                mapping=request.mapping,
                schemas=canonical_model.schemas,
                views=canonical_model.views,
                routines=canonical_model.routines,
                packages=canonical_model.packages,
                triggers=canonical_model.triggers,
                sequences=canonical_model.sequences,
                udts=canonical_model.udts,
                synonyms=canonical_model.synonyms,
                on_summary=request.options.get("on_summary"),
            )

    def _apply_dialect_translations(
        self,
        model: CanonicalSchemaModel,
        source_dialect: str,
        target_dialect: str,
    ) -> CanonicalSchemaModel:
        """Translates SQL expressions inside columns, check constraints, and views."""
        if source_dialect == target_dialect:
            return model

        mapped_tables = []
        for tbl in model.tables:
            mapped_cols = []
            for col in tbl.columns:
                def_expr = col.default_expression
                if def_expr:
                    def_expr = FunctionDialectTranslator.translate_expression(def_expr, source_dialect, target_dialect)
                    def_expr = DateTimeDialectTranslator.translate_datetime_expression(def_expr, source_dialect, target_dialect)
                    def_expr = SequenceDialectTranslator.translate_sequence_expression(def_expr, source_dialect, target_dialect)
                mapped_cols.append(
                    CanonicalColumn(
                        name=col.name,
                        ordinal_position=col.ordinal_position,
                        source_native_type=col.source_native_type,
                        canonical_type=col.canonical_type,
                        length=col.length,
                        precision=col.precision,
                        scale=col.scale,
                        byte_semantics=col.byte_semantics,
                        nullable=col.nullable,
                        default_expression=def_expr,
                        is_identity=col.is_identity,
                        identity_generation=col.identity_generation,
                        is_computed=col.is_computed,
                        computed_expression=col.computed_expression,
                        is_lob=col.is_lob,
                        is_array=col.is_array,
                        array_element_type=col.array_element_type,
                        comment=col.comment,
                        raw_metadata=col.raw_metadata,
                        extra=col.extra,
                    )
                )

            mapped_checks = []
            for ck in tbl.check_constraints:
                ck_clause = ck.check_clause
                if ck_clause:
                    ck_clause = FunctionDialectTranslator.translate_expression(ck_clause, source_dialect, target_dialect)
                    ck_clause = DateTimeDialectTranslator.translate_datetime_expression(ck_clause, source_dialect, target_dialect)
                mapped_checks.append(
                    CanonicalCheckConstraint(
                        name=ck.name,
                        table_name=ck.table_name,
                        schema_name=ck.schema_name,
                        check_clause=ck_clause,
                        is_enforced=ck.is_enforced,
                        is_not_null=ck.is_not_null,
                        not_null_column=ck.not_null_column,
                        extra=ck.extra,
                    )
                )

            mapped_tables.append(
                CanonicalTable(
                    table_name=tbl.table_name,
                    schema_name=tbl.schema_name,
                    catalog_name=tbl.catalog_name,
                    table_type=tbl.table_type,
                    storage_format=tbl.storage_format,
                    columns=tuple(mapped_cols),
                    primary_key=tbl.primary_key,
                    foreign_keys=tbl.foreign_keys,
                    unique_constraints=tbl.unique_constraints,
                    check_constraints=tuple(mapped_checks),
                    exclusion_constraints=tbl.exclusion_constraints,
                    indexes=tbl.indexes,
                    partitioning=tbl.partitioning,
                    row_format=tbl.row_format,
                    compression=tbl.compression,
                    tablespace=tbl.tablespace,
                    comment=tbl.comment,
                    raw_source_properties=tbl.raw_source_properties,
                    extra=tbl.extra,
                )
            )

        mapped_views = []
        for v in model.views:
            v_def = v.view_definition
            if v_def:
                v_def = FunctionDialectTranslator.translate_expression(v_def, source_dialect, target_dialect)
                v_def = DateTimeDialectTranslator.translate_datetime_expression(v_def, source_dialect, target_dialect)
                v_def = SequenceDialectTranslator.translate_sequence_expression(v_def, source_dialect, target_dialect)
            mapped_views.append(
                CanonicalView(
                    view_name=v.view_name,
                    schema_name=v.schema_name,
                    view_definition=v_def,
                    is_materialized=v.is_materialized,
                    materialized_refresh_mode=v.materialized_refresh_mode,
                    check_option=v.check_option,
                    is_read_only=v.is_read_only,
                    columns=v.columns,
                    dependencies=v.dependencies,
                    extra=v.extra,
                )
            )

        return CanonicalSchemaModel(
            model_id=model.model_id,
            source_vendor=model.source_vendor,
            source_version=model.source_version,
            schemas=model.schemas,
            catalogs=model.catalogs,
            tables=tuple(mapped_tables),
            views=tuple(mapped_views),
            routines=model.routines,
            packages=model.packages,
            triggers=model.triggers,
            sequences=model.sequences,
            udts=model.udts,
            synonyms=model.synonyms,
            raw_discovery_facts=model.raw_discovery_facts,
            extra=model.extra,
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
        if identity:
            vendor = identity.provider_id or identity.vendor_name
            version = identity.version.raw_version_string if hasattr(identity.version, "raw_version_string") else str(identity.version)

        snap_id = getattr(snapshot, "snapshot_id", None) or getattr(snapshot, "endpoint_id", "ep_default")

        tables: List[CanonicalTable] = []
        seen_tables = set()

        for obj_name, facts in snapshot.structures.items():
            # Parse schema and table name losslessly
            parts = obj_name.split(".")
            s_name = parts[0] if len(parts) > 1 else (getattr(facts, "schema_name", None) or "")
            t_name = parts[-1]
            seen_tables.add(f"{s_name}.{t_name}".lower())

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
                    access_m = IndexAccessMethod.UNKNOWN

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
                    part_strat = PartitionStrategy.UNKNOWN

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

        # Inventory-only tables from objects.tables
        if snapshot.objects and snapshot.objects.tables:
            for ot in snapshot.objects.tables:
                ot_name = getattr(ot, "name", str(ot))
                ot_schema = getattr(ot, "schema_name", "") or ""
                if "." in ot_name:
                    parts = ot_name.split(".")
                    ot_schema = parts[0]
                    ot_name = parts[-1]
                qual = f"{ot_schema}.{ot_name}".lower()
                if qual not in seen_tables:
                    tables.append(CanonicalTable(table_name=ot_name, schema_name=ot_schema))
                    seen_tables.add(qual)

        # Routines
        routines = []
        if snapshot.programmables and snapshot.programmables.routines:
            for r_facts in snapshot.programmables.routines:
                r_type_str = r_facts.routine_type.value if hasattr(r_facts.routine_type, "value") else str(r_facts.routine_type)
                r_kind = RoutineKind.FUNCTION if r_type_str.upper() == "FUNCTION" else RoutineKind.PROCEDURE
                routines.append(
                    CanonicalRoutine(
                        name=r_facts.name,
                        schema_name=getattr(r_facts, "schema_name", "") or "",
                        routine_type=r_kind,
                        language=r_facts.language,
                        definition_sql=r_facts.definition_sql,
                    )
                )

        # Packages
        packages = []
        if snapshot.programmables and hasattr(snapshot.programmables, "packages") and snapshot.programmables.packages:
            for p_facts in snapshot.programmables.packages:
                packages.append(
                    CanonicalPackage(
                        name=p_facts.name,
                        schema_name=getattr(p_facts, "schema_name", "") or "",
                        spec_sql=getattr(p_facts, "spec_sql", None),
                        body_sql=getattr(p_facts, "body_sql", None),
                    )
                )

        # Triggers
        triggers = []
        if snapshot.programmables and hasattr(snapshot.programmables, "triggers") and snapshot.programmables.triggers:
            for tr_facts in snapshot.programmables.triggers:
                triggers.append(
                    CanonicalTrigger(
                        name=tr_facts.name,
                        table_name=tr_facts.table_name,
                        schema_name=getattr(tr_facts, "schema_name", "") or "",
                        definition_sql=getattr(tr_facts, "definition_sql", None),
                    )
                )

        # Sequences
        sequences = []
        if snapshot.programmables and snapshot.programmables.sequences:
            for s_facts in snapshot.programmables.sequences:
                sequences.append(
                    CanonicalSequence(
                        name=s_facts.name,
                        schema_name=getattr(s_facts, "schema_name", "") or "",
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
                        schema_name=getattr(u_facts, "schema_name", "") or "",
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
            v_schema = getattr(v, "schema_name", "") or ""
            if "." in v_name and not v_schema:
                parts = v_name.split(".")
                v_schema = parts[0]
                v_name = parts[-1]
            views.append(CanonicalView(view_name=v_name, schema_name=v_schema))

        # Synonyms
        synonyms = []
        if snapshot.objects and hasattr(snapshot.objects, "synonyms") and snapshot.objects.synonyms:
            for syn in snapshot.objects.synonyms:
                syn_name = getattr(syn, "name", str(syn))
                syn_schema = getattr(syn, "schema_name", "") or ""
                target_obj = getattr(syn, "target_object", "")
                target_sch = getattr(syn, "target_schema", "") or ""
                synonyms.append(
                    CanonicalSynonym(
                        synonym_name=syn_name,
                        schema_name=syn_schema,
                        target_object_name=target_obj,
                        target_schema_name=target_sch,
                    )
                )

        unique_schemas = sorted({s for s in ({t.schema_name for t in tables} | {v.schema_name for v in views} | {r.schema_name for r in routines} | {p.schema_name for p in packages} | {tr.schema_name for tr in triggers} | {seq.schema_name for seq in sequences} | {u.schema_name for u in udts} | {syn.schema_name for syn in synonyms}) if s})
        schema_objs = [CanonicalSchema(schema_name=s) for s in unique_schemas]

        return CanonicalSchemaModel(
            model_id=f"model_{snap_id}",
            source_vendor=vendor,
            source_version=version,
            schemas=tuple(schema_objs),
            tables=tuple(tables),
            views=tuple(views),
            routines=tuple(routines),
            packages=tuple(packages),
            triggers=tuple(triggers),
            sequences=tuple(sequences),
            udts=tuple(udts),
            synonyms=tuple(synonyms),
            raw_discovery_facts=snapshot.to_dict(),
        )

    def _from_dict(self, data: Mapping[str, Any]) -> CanonicalSchemaModel:
        return CanonicalSchemaModel.from_dict(data)

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
                cached_ast = self._memo.get_parsed_ast(r.definition_sql, source_engine)
                if cached_ast is not None:
                    ast = cached_ast
                else:
                    if source_engine == "ORACLE":
                        parser = PLSQLParser(r.definition_sql)
                        ast = parser.parse()
                    elif source_engine in ("MSSQL", "SQLSERVER"):
                        parser = TSQLParser(r.definition_sql)
                        ast = parser.parse()
                    else:
                        parser = PLSQLParser(r.definition_sql)
                        ast = parser.parse()
                    self._memo.put_parsed_ast(r.definition_sql, ast, source_engine)

                # Target Procedural SQL Emission
                if target_engine in ("POSTGRESQL", "POSTGRES"):
                    res = PLpgSQLEmitter.emit_routine(ast, schema_name=r.schema_name)
                    if res.routine_name != r.name and r.name:
                        res = ProceduralConversionResult(
                            routine_name=r.name,
                            source_dialect=res.source_dialect,
                            target_dialect=res.target_dialect,
                            conversion_state=res.conversion_state,
                            emitted_sql=res.emitted_sql,
                            diagnostics=res.diagnostics,
                            required_compat_helpers=res.required_compat_helpers,
                            warnings=res.warnings,
                            extra=res.extra,
                        )
                    results.append(res)
                else:
                    # Non-PostgreSQL procedural targets require dialect rewrite
                    results.append(
                        ProceduralConversionResult(
                            routine_name=r.name,
                            source_dialect=source_engine,
                            target_dialect=target_engine,
                            conversion_state=ConversionState.MANUAL_REWRITE_REQUIRED,
                            diagnostics=(
                                ProceduralDiagnostic(
                                    severity="WARNING",
                                    rule="TARGET_PROCEDURAL_DIALECT_MANUAL_REWRITE",
                                    message=f"Target engine '{target_engine}' procedural dialect requires manual review or PL/pgSQL adaptation",
                                    line=1,
                                    column=1,
                                ),
                            ),
                            warnings=(f"Target procedural runtime for {target_engine} is not automated PL/pgSQL",),
                        )
                    )
            except Exception as e:
                logger.warning("Procedural transpilation encountered syntax/parsing exception for routine '%s': %s", r.name, e)
                results.append(
                    ProceduralConversionResult(
                        routine_name=r.name,
                        source_dialect=source_engine,
                        target_dialect=target_engine,
                        conversion_state=ConversionState.FAILED,
                        diagnostics=(
                            ProceduralDiagnostic(
                                severity="ERROR",
                                rule="ROUTINE_TRANSPILATION_ERROR",
                                message=str(e),
                                line=1,
                                column=1,
                            ),
                        ),
                    )
                )

        return results


# Default singleton Schema authority
default_schema_authority = SchemaAuthority()

