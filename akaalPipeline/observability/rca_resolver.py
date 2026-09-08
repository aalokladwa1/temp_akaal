"""akaalPipeline.observability.rca_resolver
=============================================
P7C.15 canonical resolver: composes the REAL P7C.14 CanonicalAnomalyResolver
(never recomputing detection independently) to build RCAInputs. Reuses P7C.14's
own anomaly-detection producer function to obtain the detection `data` dict,
exactly the same reuse-not-duplicate pattern P7C.14 used for P7C.13.
"""

from __future__ import annotations

from typing import Any, Optional

from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.anomaly_detection import make_anomaly_detection_producer
from akaalEngine.intelligence.producers.rca import RCAInputs
from akaalPipeline.observability.anomaly_resolver import CanonicalAnomalyResolver
from akaalPipeline.security.context import PipelineActorContext


class CanonicalRCAResolver:
    def __init__(self, anomaly_resolver: CanonicalAnomalyResolver) -> None:
        self._anomaly_resolver = anomaly_resolver

    @property
    def anomaly_resolver(self) -> CanonicalAnomalyResolver:
        return self._anomaly_resolver

    def resolve(
        self,
        migration_id: str,
        actor: PipelineActorContext,
        *,
        ownership_manager: Optional[Any] = None,
    ) -> RCAInputs:
        anomaly_inputs = self._anomaly_resolver.resolve(migration_id, actor, ownership_manager=ownership_manager)
        tenant_id = actor.organization_id

        anomaly_producer = make_anomaly_detection_producer(lambda _req, _ctx: anomaly_inputs)
        probe_request = IntelligenceRequest(
            task=IntelligenceTask.ASSESS, tenant_id=tenant_id, subject_type="migration",
            subject_id=migration_id, subject_version="v1", requested_by="p7c15-internal",
            capability="anomaly_detection",
        )
        probe_context = IntelligenceContext(
            tenant_id=tenant_id, subject_type="migration", subject_id=migration_id, subject_version="v1",
        )
        anomaly_result = anomaly_producer(probe_request, probe_context)

        dims = anomaly_inputs.runtime_health_dimensions
        return RCAInputs(
            tenant_id=tenant_id,
            migration_id=migration_id,
            anomaly_data=anomaly_result.data,
            fabric_status=str(dims.get("FABRIC", {}).get("status", "UNKNOWN")),
            validation_status=str(dims.get("VALIDATION", {}).get("status", "UNKNOWN")),
        )
