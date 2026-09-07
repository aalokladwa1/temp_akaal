"""akaalPipeline.observability.remediation_resolver
======================================================
P7C.18 canonical resolver: composes the REAL P7C.15 CanonicalRCAResolver
(never recomputing RCA independently) to build RemediationInputs.
"""

from __future__ import annotations

from typing import Any, Optional

from akaalEngine.intelligence.identity.fingerprint import compute_context_fingerprint
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.rca import make_rca_producer
from akaalEngine.intelligence.producers.remediation import RemediationInputs
from akaalPipeline.observability.rca_resolver import CanonicalRCAResolver
from akaalPipeline.security.context import PipelineActorContext


class CanonicalRemediationResolver:
    def __init__(self, rca_resolver: CanonicalRCAResolver) -> None:
        self._rca_resolver = rca_resolver

    @property
    def rca_resolver(self) -> CanonicalRCAResolver:
        return self._rca_resolver

    def resolve(
        self,
        migration_id: str,
        actor: PipelineActorContext,
        *,
        ownership_manager: Optional[Any] = None,
    ) -> RemediationInputs:
        rca_inputs = self._rca_resolver.resolve(migration_id, actor, ownership_manager=ownership_manager)
        tenant_id = actor.organization_id

        rca_producer = make_rca_producer(lambda _req, _ctx: rca_inputs)
        probe_request = IntelligenceRequest(
            task=IntelligenceTask.EXPLAIN, tenant_id=tenant_id, subject_type="migration",
            subject_id=migration_id, subject_version="v1", requested_by="p7c18-internal",
            capability="root_cause_analysis",
        )
        probe_context = IntelligenceContext(
            tenant_id=tenant_id, subject_type="migration", subject_id=migration_id, subject_version="v1",
        )
        rca_result = rca_producer(probe_request, probe_context)

        return RemediationInputs(
            tenant_id=tenant_id,
            migration_id=migration_id,
            requested_by=actor.actor_id,
            context_fingerprint=compute_context_fingerprint(probe_context),
            rca_data=rca_result.data,
            fabric_status=rca_inputs.fabric_status,
            validation_status=rca_inputs.validation_status,
        )
