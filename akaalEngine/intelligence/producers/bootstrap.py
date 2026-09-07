"""akaalEngine.intelligence.producers.bootstrap
================================================
Registers every Campaign B (P7C.7-P7C.12) producer onto a shared IntelligenceKernel
instance, e.g. the one akaalPipeline.application.unified_caller.PipelineUnifiedCaller
constructs for production use -- the same kernel instance reachable through the
real akaalIPC -> akaalPipeline -> akaalEngine.intelligence seam already proven for
P7C.1/P7C.6.

Resolver design (deliberately conservative, no fabricated wiring): schema-model-
consuming producers (estate assessment, wave planning, schema optimization, SQL
translation) resolve their CanonicalSchemaModel from `request.parameters
["schema_model"]` -- data the AUTHENTICATED CALLER supplies inline about their own
migration, never looked up by a caller-supplied foreign artifact/migration ID. This
avoids introducing a cross-tenant read path: akaalPipeline.state.artifacts.
ImmutableArtifact/ArtifactRegistry has no tenant_id field of its own (verified by
inspection), so resolving a schema model by an arbitrary caller-supplied artifact_id
would bypass tenant isolation entirely. Wiring these producers instead to a
tenant-scoped "schema model for migration_id" canonical query is a legitimate future
integration step once such a query exists in akaalEngine.schema.authority -- it does
not exist in this repository today, and is not fabricated here.
"""

from __future__ import annotations

from typing import Any

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.capacity_simulation import make_capacity_simulation_producer
from akaalEngine.intelligence.producers.cross_migration_patterns import make_cross_migration_pattern_producer
from akaalEngine.intelligence.producers.estate_assessment import make_estate_assessment_producer
from akaalEngine.intelligence.producers.schema_optimization import make_schema_optimization_producer
from akaalEngine.intelligence.producers.sql_translation import make_sql_translation_producer
from akaalEngine.intelligence.producers.strategy_generation import make_strategy_generation_producer
from akaalEngine.intelligence.producers.wave_planning import make_wave_planning_producer
from akaalEngine.schema.models.schema import CanonicalSchemaModel


def _inline_schema_model_resolver(request: IntelligenceRequest, context: IntelligenceContext) -> Any:
    raw = request.parameters.get("schema_model")
    if not raw:
        raise IntelligenceValidationError(
            "This capability requires request.parameters['schema_model'] (the "
            "caller's own canonical schema model data for this migration)."
        )
    return CanonicalSchemaModel.from_dict(raw)


def register_all_campaign_b_producers(kernel: IntelligenceKernel) -> None:
    kernel.register_producer(
        IntelligenceTask.ASSESS,
        make_estate_assessment_producer(_inline_schema_model_resolver),
        capability="estate_assessment",
    )
    kernel.register_producer(
        IntelligenceTask.OPTIMIZE,
        make_strategy_generation_producer(),
        capability="strategy_generation",
    )
    kernel.register_producer(
        IntelligenceTask.OPTIMIZE,
        make_wave_planning_producer(_inline_schema_model_resolver),
        capability="wave_planning",
    )
    kernel.register_producer(
        IntelligenceTask.OPTIMIZE,
        make_schema_optimization_producer(_inline_schema_model_resolver),
        capability="schema_optimization",
    )
    kernel.register_producer(
        IntelligenceTask.CONVERT,
        make_sql_translation_producer(_inline_schema_model_resolver),
        capability="sql_translation",
    )
    kernel.register_producer(
        IntelligenceTask.SIMULATE,
        make_capacity_simulation_producer(),
        capability="capacity_scenario",
    )
    kernel.register_producer(
        IntelligenceTask.COMPARE,
        make_cross_migration_pattern_producer(),
        capability="cross_migration_patterns",
    )
