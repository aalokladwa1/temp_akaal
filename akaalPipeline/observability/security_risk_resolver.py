"""akaalPipeline.observability.security_risk_resolver
========================================================
P7C.19 canonical resolver: composes the REAL P7C.18 CanonicalRemediationResolver
(itself composing RCA/anomaly/health) to build SecurityRiskInputs -- never
recomputes any of those upstream conclusions independently.
"""

from __future__ import annotations

from typing import Any, Optional

from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.remediation import make_remediation_producer
from akaalEngine.intelligence.producers.security_risk import SecurityRiskInputs
from akaalPipeline.observability.remediation_resolver import CanonicalRemediationResolver
from akaalPipeline.security.context import PipelineActorContext


class CanonicalSecurityRiskResolver:
    def __init__(self, remediation_resolver: CanonicalRemediationResolver) -> None:
        self._remediation_resolver = remediation_resolver

    def resolve(
        self,
        migration_id: str,
        actor: PipelineActorContext,
        *,
        ownership_manager: Optional[Any] = None,
    ) -> SecurityRiskInputs:
        remediation_inputs = self._remediation_resolver.resolve(migration_id, actor, ownership_manager=ownership_manager)
        tenant_id = actor.organization_id

        remediation_producer = make_remediation_producer(lambda _req, _ctx: remediation_inputs)
        probe_request = IntelligenceRequest(
            task=IntelligenceTask.RECOMMEND, tenant_id=tenant_id, subject_type="migration",
            subject_id=migration_id, subject_version="v1", requested_by="p7c19-internal",
            capability="governed_remediation",
        )
        probe_context = IntelligenceContext(
            tenant_id=tenant_id, subject_type="migration", subject_id=migration_id, subject_version="v1",
        )
        remediation_result = remediation_producer(probe_request, probe_context)
        proposal = remediation_result.data.get("action_proposal")

        return SecurityRiskInputs(
            tenant_id=tenant_id,
            migration_id=migration_id,
            fabric_status=remediation_inputs.fabric_status,
            validation_status=remediation_inputs.validation_status,
            pending_remediation_action_type=proposal.get("action_type") if proposal else None,
        )
