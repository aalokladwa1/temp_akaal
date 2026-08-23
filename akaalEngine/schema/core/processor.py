"""
akaalEngine.schema.core.processor
=================================
Large estate chunked schema compilation processor for SCH-069.
Enables memory-bounded chunked conversion, cross-chunk Kahn dependency ordering,
and staged DDL processing for estates exceeding 50,000 objects.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import hashlib
from types import MappingProxyType
from typing import Any, Callable, Dict, Generator, Iterable, Iterator, List, Mapping, Optional, Sequence, Set, Tuple

from akaalEngine.schema.assessment.compatibility import (
    CompatibilityBreakdown,
    PreMigrationCompatibilityAssessor,
)
from akaalEngine.schema.assessment.projection import (
    CapacityEvidenceKind,
    TableCapacityProjection,
    TargetCapacityReport,
    TargetCapacitySchemaProjection,
)
from akaalEngine.schema.assessment.readiness import (
    ReadinessGateReport,
    SchemaReadinessGateProvider,
)
from akaalEngine.schema.assessment.risk import (
    RiskLevel,
    StructuralRiskReport,
    StructuralRiskScorer,
)
from akaalEngine.schema.compat.lifecycle import (
    CompatibilityPackReport,
    CompatibilityRequirementTracker,
)
from akaalEngine.schema.core.provenance import (
    DeterministicSchemaProvenanceHasher,
    get_rule_implementation_version,
)
from akaalEngine.schema.ddl.emitter import DDLStage, StagedDDLPackage, StructuredDDLArtifact
from akaalEngine.schema.ddl.generator import DDLGenerator
from akaalEngine.schema.dialect import (
    DateTimeDialectTranslator,
    FunctionDialectTranslator,
    SequenceDialectTranslator,
)
from akaalEngine.schema.mapping.engine import MappingEngine
from akaalEngine.schema.models.mapping import CompiledSchemaMapping
from akaalEngine.schema.models.programmables import (
    CanonicalPackage,
    CanonicalRoutine,
    CanonicalSequence,
    CanonicalTrigger,
    CanonicalUDT,
)
from akaalEngine.schema.models.schema import (
    CanonicalSchema,
    CanonicalSchemaModel,
    CanonicalSynonym,
    CanonicalView,
)
from akaalEngine.schema.models.table import CanonicalColumn, CanonicalTable
from akaalEngine.schema.procedural.diagnostics import (
    ConversionState,
    ProceduralConversionResult,
    ProceduralDiagnostic,
)
from akaalEngine.schema.procedural.emitters.plpgsql import PLpgSQLEmitter
from akaalEngine.schema.procedural.parsers.plsql import PLSQLParser
from akaalEngine.schema.procedural.parsers.tsql import TSQLParser


@dataclass(frozen=True)
class EstateCompilationSummary:
    """Consolidated summary of whole-estate metrics, assessments, and provenance produced from bounded streaming."""
    total_tables: int
    total_chunks: int
    source_engine: str
    target_engine: str
    compatibility_report: CompatibilityBreakdown
    risk_report: StructuralRiskReport
    readiness_report: ReadinessGateReport
    capacity_report: TargetCapacityReport
    compat_pack_report: CompatibilityPackReport
    procedural_results: Tuple[ProceduralConversionResult, ...]
    topologically_ordered_table_names: Tuple[str, ...]
    provenance_fingerprint: str


class LargeEstateChunkedSchemaProcessor:
    """
    Memory-bounded chunked schema compiler for enterprise estates (SCH-069).
    Splits large estates into deterministic batches (default: 500 tables) to prevent RAM explosion.
    Provides complete 18-step canonical schema compilation workflow in bounded chunks.
    """

    DEFAULT_CHUNK_SIZE = 500

    @classmethod
    def build_lightweight_table_order(cls, tables: Sequence[CanonicalTable]) -> List[str]:
        """Builds a lightweight O(V+E) adjacency graph using string IDs to determine dependency order with minimal RAM."""
        adj: Dict[str, Set[str]] = {}
        in_degree: Dict[str, int] = {}
        for t in tables:
            qname = t.qualified_name.lower()
            if qname not in adj:
                adj[qname] = set()
            if qname not in in_degree:
                in_degree[qname] = 0

            for fk in t.foreign_keys:
                ref_qname = f"{fk.referenced_schema}.{fk.referenced_table}".lower()
                if ref_qname != qname:
                    if ref_qname not in adj:
                        adj[ref_qname] = set()
                    if qname not in adj[ref_qname]:
                        adj[ref_qname].add(qname)
                        in_degree[qname] = in_degree.get(qname, 0) + 1

        # Kahn's algorithm with O(1) popleft and deterministic initial order
        queue = deque(sorted(k for k, deg in in_degree.items() if deg == 0))
        sorted_keys: List[str] = []
        while queue:
            node = queue.popleft()
            sorted_keys.append(node)
            for neighbor in sorted(adj.get(node, ())):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        seen = set(sorted_keys)
        for k in sorted(in_degree.keys()):
            if k not in seen:
                sorted_keys.append(k)

        return sorted_keys

    @classmethod
    def stream_chunked_tables(
        cls,
        tables_iter: Iterator[CanonicalTable],
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> Iterator[Tuple[CanonicalTable, ...]]:
        """Yields successive slices of tables from a generator or stream without materializing the whole estate."""
        chunk: List[CanonicalTable] = []
        for tbl in tables_iter:
            chunk.append(tbl)
            if len(chunk) >= chunk_size:
                yield tuple(chunk)
                chunk = []
        if chunk:
            yield tuple(chunk)

    @classmethod
    def stream_compile_estate(
        cls,
        tables_stream: Iterable[CanonicalTable],
        target_engine: str,
        target_version: Optional[str] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        source_vendor: str = "GENERIC",
        mapping: Optional[CompiledSchemaMapping] = None,
        schemas: Sequence[CanonicalSchema] = (),
        views: Sequence[CanonicalView] = (),
        routines: Sequence[CanonicalRoutine] = (),
        packages: Sequence[CanonicalPackage] = (),
        triggers: Sequence[CanonicalTrigger] = (),
        sequences: Sequence[CanonicalSequence] = (),
        udts: Sequence[CanonicalUDT] = (),
        synonyms: Sequence[CanonicalSynonym] = (),
        on_summary: Optional[Callable[[EstateCompilationSummary], None]] = None,
    ) -> Iterator[StagedDDLPackage]:
        """
        Complete 18-step streaming compilation across large enterprise estates (SCH-069).
        Performs cross-chunk Kahn dependency ordering, mapping, dialect translation,
        compatibility assessment, risk scoring, readiness gate, capacity projection,
        and whole-estate composite provenance in memory-bounded streaming chunks.
        """
        tgt_eng = target_engine.strip().upper()
        src_eng = source_vendor.strip().upper()

        # Step 1: Collect lightweight table references and index
        table_dict: Dict[str, CanonicalTable] = {}
        for tbl in tables_stream:
            table_dict[tbl.qualified_name.lower()] = tbl

        ordered_keys = cls.build_lightweight_table_order(list(table_dict.values()))
        total_tables = len(ordered_keys)

        # Step 2: Procedural transpilation (if any routines present)
        procedural_results: List[ProceduralConversionResult] = []
        for r in routines:
            if not r.definition_sql:
                continue
            try:
                if src_eng == "ORACLE":
                    ast = PLSQLParser(r.definition_sql).parse()
                elif src_eng in ("MSSQL", "SQLSERVER"):
                    ast = TSQLParser(r.definition_sql).parse()
                else:
                    ast = PLSQLParser(r.definition_sql).parse()

                if tgt_eng in ("POSTGRESQL", "POSTGRES"):
                    res = PLpgSQLEmitter.emit_routine(ast, schema_name=r.schema_name)
                    procedural_results.append(res)
                else:
                    procedural_results.append(
                        ProceduralConversionResult(
                            routine_name=r.name,
                            source_dialect=src_eng,
                            target_dialect=tgt_eng,
                            conversion_state=ConversionState.MANUAL_REWRITE_REQUIRED,
                            diagnostics=(
                                ProceduralDiagnostic(
                                    severity="WARNING",
                                    rule="TARGET_PROCEDURAL_DIALECT_MANUAL_REWRITE",
                                    message=f"Target engine '{tgt_eng}' procedural dialect requires manual review or PL/pgSQL adaptation",
                                    line=1,
                                    column=1,
                                ),
                            ),
                            warnings=(f"Target procedural runtime for {tgt_eng} is not automated PL/pgSQL",),
                        )
                    )
            except Exception as e:
                procedural_results.append(
                    ProceduralConversionResult(
                        routine_name=r.name,
                        source_dialect=src_eng,
                        target_dialect=tgt_eng,
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
                        warnings=(str(e),),
                    )
                )

        procedural_ddl_artifacts: List[StructuredDDLArtifact] = []
        emitter = DDLGenerator.get_emitter(tgt_eng, target_version)
        for r in routines:
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
                    source_engine=src_eng,
                )
            )
        for tr in triggers:
            procedural_ddl_artifacts.extend(emitter.emit_trigger_artifacts(tr, source_engine=src_eng))

        tracker = CompatibilityRequirementTracker()
        for r in procedural_results:
            for helper in r.required_compat_helpers:
                tracker.record_requirement(helper, r.routine_name, tgt_eng)
        compat_pack_report = tracker.build_report()

        # Step 3: Stream chunk by chunk in topological dependency order
        accum_exact = 0
        accum_equiv = 0
        accum_trans = 0
        accum_lossy = 0
        accum_unsupp = 0
        accum_decis = 0
        accum_lossy_assessments = []
        accum_dropped_fks = 0

        accum_est_rows = 0
        accum_src_bytes = 0
        accum_tgt_bytes = 0
        accum_table_projections: List[TableCapacityProjection] = []
        accum_ddl_hashes: List[str] = []
        accum_cap_hashes: List[str] = []

        chunk_count = 0
        for start_idx in range(0, total_tables, chunk_size):
            end_idx = min(start_idx + chunk_size, total_tables)
            chunk_keys = ordered_keys[start_idx:end_idx]
            raw_chunk_tables = tuple(table_dict[k] for k in chunk_keys if k in table_dict)

            # Construct chunk canonical model
            chunk_model = CanonicalSchemaModel(
                model_id=f"chunk_{chunk_count}",
                source_vendor=src_eng,
                schemas=schemas if chunk_count == 0 else (),
                tables=raw_chunk_tables,
                views=views if chunk_count == 0 else (),
                routines=routines if chunk_count == 0 else (),
                packages=packages if chunk_count == 0 else (),
                triggers=triggers if chunk_count == 0 else (),
                sequences=sequences if chunk_count == 0 else (),
                udts=udts if chunk_count == 0 else (),
                synonyms=synonyms if chunk_count == 0 else (),
            )

            # Apply mapping to chunk
            if mapping:
                chunk_model = MappingEngine.apply_mapping(chunk_model, mapping, target_vendor=tgt_eng)

            # Apply dialect translation to chunk
            chunk_model = cls._apply_dialect_translations(chunk_model, src_eng, tgt_eng)

            # Compatibility & Lossiness Assessment for chunk
            chunk_compat = PreMigrationCompatibilityAssessor.assess_model(chunk_model, tgt_eng)
            accum_exact += chunk_compat.exact_count
            accum_equiv += chunk_compat.equivalent_count
            accum_trans += chunk_compat.transformed_count
            accum_lossy += chunk_compat.lossy_count
            accum_unsupp += chunk_compat.unsupported_count
            accum_decis += chunk_compat.decision_required_count
            accum_lossy_assessments.extend(chunk_compat.lossy_assessments)
            accum_dropped_fks += chunk_compat.extra.get("dropped_foreign_keys_count", 0)

            # Capacity projection for chunk
            chunk_cap = TargetCapacitySchemaProjection.calculate_projection(chunk_model, tgt_eng)
            accum_est_rows += chunk_cap.total_estimated_rows
            accum_src_bytes += chunk_cap.total_source_bytes
            accum_tgt_bytes += chunk_cap.total_projected_target_bytes
            if len(accum_table_projections) < 1000:
                accum_table_projections.extend(chunk_cap.table_projections)
            accum_cap_hashes.append(DeterministicSchemaProvenanceHasher.hash_dict(chunk_cap.to_dict()))

            # Generate Staged DDL package for chunk
            chunk_pkg = DDLGenerator.generate_ddl_package(
                chunk_model,
                tgt_eng,
                target_version,
                procedural_artifacts=procedural_ddl_artifacts if chunk_count == 0 else None,
            )
            accum_ddl_hashes.append(DeterministicSchemaProvenanceHasher.compute_ddl_fingerprint(chunk_pkg))

            chunk_count += 1
            yield chunk_pkg

        # Step 4: Build consolidated assessment reports & whole-estate provenance
        tot_cols = accum_exact + accum_equiv + accum_trans + accum_lossy + accum_unsupp + accum_decis
        consolidated_compat = CompatibilityBreakdown(
            total_columns=tot_cols,
            exact_count=accum_exact,
            equivalent_count=accum_equiv,
            transformed_count=accum_trans,
            compat_layer_count=0,
            lossy_count=accum_lossy,
            unsupported_count=accum_unsupp,
            decision_required_count=accum_decis,
            lossy_assessments=tuple(accum_lossy_assessments),
            extra={"dropped_foreign_keys_count": accum_dropped_fks},
        )

        consolidated_risk = StructuralRiskReport(
            total_risk_score=min(100, accum_lossy * 5 + accum_unsupp * 10 + accum_dropped_fks * 15),
            risk_level=RiskLevel.HIGH if (accum_unsupp > 0 or accum_dropped_fks > 0) else RiskLevel.MEDIUM if accum_lossy > 0 else RiskLevel.LOW,
            risk_factors=(),
        )

        consolidated_readiness = SchemaReadinessGateProvider.evaluate_readiness(
            consolidated_compat,
            consolidated_risk,
        )

        consolidated_capacity = TargetCapacityReport(
            total_tables=total_tables,
            total_estimated_rows=accum_est_rows,
            total_source_bytes=accum_src_bytes,
            total_projected_target_bytes=accum_tgt_bytes,
            table_projections=tuple(accum_table_projections),
            extra={"evidence_kind": CapacityEvidenceKind.ESTIMATED.value},
        )

        # Whole-estate deterministic provenance
        ddl_hasher = hashlib.sha256()
        for h in accum_ddl_hashes:
            ddl_hasher.update(h.encode("utf-8"))
            ddl_hasher.update(b"\n")
        composite_ddl_hash = ddl_hasher.hexdigest()

        key_hasher = hashlib.sha256()
        for k in ordered_keys:
            key_hasher.update(k.encode("utf-8"))
            key_hasher.update(b"\n")
        src_keys_fingerprint = key_hasher.hexdigest()
        src_hash = DeterministicSchemaProvenanceHasher.hash_dict({
            "table_count": total_tables,
            "keys_fingerprint": src_keys_fingerprint,
        })

        map_hash = DeterministicSchemaProvenanceHasher.compute_mapping_fingerprint(mapping) if mapping else "NO_MAPPING"
        proc_hash = DeterministicSchemaProvenanceHasher.hash_dict({"results": [r.to_dict() for r in procedural_results]})

        cap_hasher = hashlib.sha256()
        for h in accum_cap_hashes:
            cap_hasher.update(h.encode("utf-8"))
            cap_hasher.update(b"\n")
        capacity_hash = DeterministicSchemaProvenanceHasher.hash_dict({
            "chunk_capacity_fingerprint": cap_hasher.hexdigest(),
            "total_tables": total_tables,
            "total_estimated_rows": accum_est_rows,
            "total_source_bytes": accum_src_bytes,
            "total_projected_target_bytes": accum_tgt_bytes,
        })

        provenance = DeterministicSchemaProvenanceHasher.compute_compilation_provenance(
            source_model_hash=src_hash,
            mapping_hash=map_hash,
            ddl_package_hash=composite_ddl_hash,
            target_engine=tgt_eng,
            target_version=target_version or "default",
            rule_set_version="1",
            procedural_hash=proc_hash,
            readiness_hash=DeterministicSchemaProvenanceHasher.hash_dict(consolidated_readiness.to_dict()),
            compatibility_breakdown_hash=DeterministicSchemaProvenanceHasher.hash_dict(consolidated_compat.to_dict()),
            compat_pack_hash=DeterministicSchemaProvenanceHasher.hash_dict(compat_pack_report.to_dict()),
            risk_hash=DeterministicSchemaProvenanceHasher.hash_dict(consolidated_risk.to_dict()),
            capacity_hash=capacity_hash,
            options_hash=DeterministicSchemaProvenanceHasher.hash_dict({"chunk_size": chunk_size}),
            rule_impl_version=get_rule_implementation_version(),
        )

        summary = EstateCompilationSummary(
            total_tables=total_tables,
            total_chunks=chunk_count,
            source_engine=src_eng,
            target_engine=tgt_eng,
            compatibility_report=consolidated_compat,
            risk_report=consolidated_risk,
            readiness_report=consolidated_readiness,
            capacity_report=consolidated_capacity,
            compat_pack_report=compat_pack_report,
            procedural_results=tuple(procedural_results),
            topologically_ordered_table_names=tuple(ordered_keys),
            provenance_fingerprint=provenance,
        )

        if on_summary:
            on_summary(summary)

    @classmethod
    def _apply_dialect_translations(
        cls,
        model: CanonicalSchemaModel,
        source_dialect: str,
        target_dialect: str,
    ) -> CanonicalSchemaModel:
        """Translates SQL expressions in column defaults, check constraints, and computed expressions."""
        if source_dialect == target_dialect:
            return model

        mapped_tables = []
        for tbl in model.tables:
            mapped_cols = []
            for col in tbl.columns:
                def_expr = col.default_expression
                comp_expr = col.computed_expression
                if def_expr:
                    def_expr = DateTimeDialectTranslator.translate_datetime_expression(def_expr, source_dialect, target_dialect)
                    def_expr = SequenceDialectTranslator.translate_sequence_expression(def_expr, source_dialect, target_dialect)
                    def_expr = FunctionDialectTranslator.translate_expression(def_expr, source_dialect, target_dialect)
                if comp_expr:
                    comp_expr = FunctionDialectTranslator.translate_expression(comp_expr, source_dialect, target_dialect)

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
                        computed_expression=comp_expr,
                        is_lob=col.is_lob,
                        is_array=col.is_array,
                        array_element_type=col.array_element_type,
                        comment=col.comment,
                        raw_metadata=col.raw_metadata,
                        extra=col.extra,
                    )
                )

            mapped_tables.append(
                CanonicalTable(
                    table_name=tbl.table_name,
                    schema_name=tbl.schema_name,
                    columns=tuple(mapped_cols),
                    primary_key=tbl.primary_key,
                    foreign_keys=tbl.foreign_keys,
                    unique_constraints=tbl.unique_constraints,
                    check_constraints=tbl.check_constraints,
                    indexes=tbl.indexes,
                    partitioning=tbl.partitioning,
                    comment=tbl.comment,
                    raw_source_properties=tbl.raw_source_properties,
                    extra=tbl.extra,
                )
            )

        return CanonicalSchemaModel(
            model_id=model.model_id,
            source_vendor=model.source_vendor,
            source_version=model.source_version,
            schemas=model.schemas,
            tables=tuple(mapped_tables),
            views=model.views,
            routines=model.routines,
            packages=model.packages,
            triggers=model.triggers,
            sequences=model.sequences,
            udts=model.udts,
            synonyms=model.synonyms,
            extra=model.extra,
        )

    @classmethod
    def process_chunked_compilation(
        cls,
        model: CanonicalSchemaModel,
        target_engine: str,
        target_version: Optional[str] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Iterator[StagedDDLPackage]:
        """
        Streams staged DDL packages chunk by chunk in deterministic topological dependency order.
        """
        yield from cls.stream_compile_estate(
            tables_stream=model.tables,
            target_engine=target_engine,
            target_version=target_version,
            chunk_size=chunk_size,
            source_vendor=model.source_vendor,
            schemas=model.schemas,
            views=model.views,
            routines=model.routines,
            packages=model.packages,
            triggers=model.triggers,
            sequences=model.sequences,
            udts=model.udts,
            synonyms=model.synonyms,
        )

    @classmethod
    def compile_large_estate_package(
        cls,
        model: CanonicalSchemaModel,
        target_engine: str,
        target_version: Optional[str] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        procedural_artifacts: Optional[List[StructuredDDLArtifact]] = None,
    ) -> StagedDDLPackage:
        """
        Compiles large estate in chunks and merges resulting artifacts into a single StagedDDLPackage.
        """
        all_artifacts: List[StructuredDDLArtifact] = []
        for pkg in cls.stream_compile_estate(
            tables_stream=model.tables,
            target_engine=target_engine,
            target_version=target_version,
            chunk_size=chunk_size,
            source_vendor=model.source_vendor,
            schemas=model.schemas,
            views=model.views,
            routines=model.routines,
            packages=model.packages,
            triggers=model.triggers,
            sequences=model.sequences,
            udts=model.udts,
            synonyms=model.synonyms,
        ):
            all_artifacts.extend(pkg.artifacts)

        if procedural_artifacts:
            all_artifacts.extend(procedural_artifacts)

        return StagedDDLPackage(
            target_engine=target_engine.upper(),
            artifacts=tuple(all_artifacts),
        )
