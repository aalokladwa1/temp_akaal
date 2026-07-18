"""
Akaal — Canonical Report Builder
================================
Assembles canonical CanonicalMigrationModel artifacts from evaluated normalization pipeline results.
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List
from akaal.decoder.models.decoder_context import DecoderContext
from akaal.decoder.models.canonical_graph import CanonicalObjectGraph
from akaal.decoder.models.canonical_capability import CanonicalCapabilityModel
from akaal.decoder.models.canonical_lineage import CanonicalLineage
from akaal.decoder.models.canonical_diagnostic import CanonicalDiagnostic
from akaal.decoder.models.canonical_manifest import CanonicalManifest
from akaal.decoder.models.canonical_migration_model import CanonicalMigrationModel
from akaal.decoder.models.decoder_trace import DecoderExecutionTrace


class CanonicalReportBuilder:
    """Assembles final immutable CanonicalMigrationModel."""

    @staticmethod
    def build_model(
        ctx: DecoderContext,
        graph: CanonicalObjectGraph,
        capability_model: CanonicalCapabilityModel,
        semantic_summary: Dict[str, Any],
        lineage: CanonicalLineage,
        diagnostics: List[CanonicalDiagnostic],
        trace: DecoderExecutionTrace,
    ) -> CanonicalMigrationModel:
        manifest = CanonicalManifest(
            schema_version="1.0.0",
            capability_model_version="1.0.0",
            compatibility_matrix_version="1.0.0",
            function_library_version="1.0.0",
            expression_ast_version="1.0.0",
            dependency_graph_version="1.0.0",
            decoder_version=ctx.decoder_version,
        )

        metadata = {
            "source_engine": ctx.discovery_report.engine_info.system_type if ctx.discovery_report.engine_info else "GENERIC",
            "target_engine": ctx.migration_ruleset.metadata.get("target_engine", "POSTGRESQL") if ctx.migration_ruleset else "POSTGRESQL",
            "correlation_id": ctx.correlation_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "validation_profile": ctx.validation_profile.value if hasattr(ctx.validation_profile, "value") else str(ctx.validation_profile),
        }

        diag_dicts = [d.to_dict() for d in diagnostics]

        temp_dict = {
            "source_engine": metadata.get("source_engine"),
            "target_engine": metadata.get("target_engine"),
            "validation_profile": metadata.get("validation_profile"),
            "capability_model": capability_model.to_dict(),
            "canonical_graph": graph.to_dict(),
            "semantic_mappings": semantic_summary,
            "diagnostics": diag_dicts,
        }
        checksum_val = hashlib.sha256(json.dumps(temp_dict, default=str, sort_keys=True).encode("utf-8")).hexdigest()

        manifest.model_checksum = checksum_val

        return CanonicalMigrationModel(
            sha256_checksum=checksum_val,
            metadata=metadata,
            capability_model=capability_model.to_dict(),
            canonical_graph=graph.to_dict(),
            semantic_mappings=semantic_summary,
            canonical_manifest=manifest.to_dict(),
            decoder_metrics={"total_objects_normalized": len(graph.get_all_objects())},
            execution_trace=trace.to_dict(),
            diagnostics=diag_dicts,
            lineage=lineage.to_dict(),
        )
