"""
Akaal — Normalization Pipeline Orchestrator Engine
===================================================
Pipeline orchestrator running normalization stages in strict single-responsibility sequence.
"""

import time
from typing import Dict, Any, List, Tuple
from akaal.decoder.models.decoder_context import DecoderContext
from akaal.decoder.models.decoder_trace import DecoderExecutionTrace, TraceStep
from akaal.decoder.models.canonical_migration_model import CanonicalMigrationModel
from akaal.decoder.models.canonical_capability import CanonicalCapabilityModel
from akaal.decoder.models.canonical_manifest import CanonicalManifest
from akaal.decoder.engine.datatype_engine import DatatypeEngine
from akaal.decoder.engine.metadata_engine import MetadataEngine
from akaal.decoder.engine.expression_engine import ExpressionEngine
from akaal.decoder.engine.compatibility_engine import CompatibilityEngine
from akaal.decoder.engine.dependency_engine import DependencyEngine
from akaal.decoder.engine.lineage_engine import LineageEngine
from akaal.decoder.engine.validation_engine import ValidationEngine
from akaal.decoder.reporting.canonical_report_builder import CanonicalReportBuilder


class NormalizationEngine:
    """Orchestrates normalization pipeline stages."""

    def normalize(self, ctx: DecoderContext) -> Tuple[CanonicalMigrationModel, DecoderExecutionTrace]:
        t0 = time.time()
        trace = DecoderExecutionTrace(correlation_id=ctx.correlation_id)

        # 1. Metadata Engine & Datatype Engine
        meta_engine = MetadataEngine()
        graph, schemas = meta_engine.normalize_metadata(ctx.discovery_report)

        trace.add_step(TraceStep(
            normalization_order=1,
            engine_name="MetadataEngine",
            object_identifier="SCHEMA_METADATA",
            status="NORMALIZED",
            metadata_mapped=True,
            datatype_mapped=True,
        ))

        # 2. Expression Engine
        expr_engine = ExpressionEngine()
        for obj in graph.get_all_objects():
            if hasattr(obj, "default_expression") and isinstance(obj.default_expression, str):
                ast_node = expr_engine.parse_expression(obj.default_expression)
                obj.default_expression = ast_node.to_dict()

        trace.add_step(TraceStep(
            normalization_order=2,
            engine_name="ExpressionEngine",
            object_identifier="EXPRESSION_AST",
            status="NORMALIZED",
            expression_mapped=True,
        ))

        # 3. Compatibility Engine
        comp_engine = CompatibilityEngine()
        semantic_summary = comp_engine.evaluate_compatibility(graph)

        trace.add_step(TraceStep(
            normalization_order=3,
            engine_name="CompatibilityEngine",
            object_identifier="SEMANTIC_EQUIVALENCE",
            status="NORMALIZED",
            compatibility_resolved=True,
        ))

        # 4. Dependency Engine
        dep_engine = DependencyEngine()
        ordered_objs, dep_summary = dep_engine.resolve_dependencies(graph)

        trace.add_step(TraceStep(
            normalization_order=4,
            engine_name="DependencyEngine",
            object_identifier="DEPENDENCY_DAG",
            status="NORMALIZED",
        ))

        # 5. Lineage Engine
        lin_engine = LineageEngine()
        lineage = lin_engine.record_lineage(graph, ctx.correlation_id)

        trace.add_step(TraceStep(
            normalization_order=5,
            engine_name="LineageEngine",
            object_identifier="LINEAGE_STAGE_1",
            status="NORMALIZED",
        ))

        # 6. Validation Engine
        val_engine = ValidationEngine()
        is_valid, diagnostics = val_engine.validate_graph(graph, ctx)

        trace.add_step(TraceStep(
            normalization_order=6,
            engine_name="ValidationEngine",
            object_identifier="GRAPH_VALIDATION",
            status="NORMALIZED" if is_valid else "WARNED",
            validation_passed=is_valid,
        ))

        # 7. Capability Model
        cap_model = CanonicalCapabilityModel()
        cap_model.set_capability("Transactions", True, {"isolation": "READ_COMMITTED"})
        cap_model.set_capability("Partitioning", True, {"supported_strategies": ["RANGE", "HASH"]})

        t1 = time.time()
        trace.total_trace_duration_ms = (t1 - t0) * 1000.0

        # Build CanonicalMigrationModel
        model = CanonicalReportBuilder.build_model(
            ctx=ctx,
            graph=graph,
            capability_model=cap_model,
            semantic_summary=semantic_summary,
            lineage=lineage,
            diagnostics=diagnostics,
            trace=trace,
        )

        return model, trace
