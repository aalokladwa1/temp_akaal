"""akaalEngine.intelligence.gateway.routing
============================================
Policy-based model routing (P7C.4). Security/residency/sensitivity constraints
are applied BEFORE cost/latency preference (P7C brief §P7C.4 "Routing"), and
routing fails closed -- a request that cannot legally be routed raises a typed
error rather than silently degrading to a disallowed provider/region.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, List, Optional

from akaalEngine.intelligence.gateway.errors import (
    ModelResidencyProhibitedError,
    ModelSensitivityProhibitedError,
    ModelUnavailableError,
    NoCompatibleModelError,
)
from akaalEngine.intelligence.gateway.registry import (
    ApprovalStatus,
    DataClassification,
    ModelDescriptor,
    ModelRegistry,
)


@dataclass(frozen=True)
class RoutingRequest:
    required_capability: str
    tenant_id: str
    data_classification: DataClassification = DataClassification.INTERNAL
    allowed_regions: Optional[FrozenSet[str]] = None
    prefer_lowest_cost: bool = True

    def __post_init__(self) -> None:
        if self.allowed_regions is not None:
            object.__setattr__(self, "allowed_regions", frozenset(self.allowed_regions))


class ModelRouter:
    """Stateless router over a ModelRegistry. Every call re-evaluates current
    registry state (health/approval can change between calls -- P7C brief
    "Provider health transitions" / "Failover")."""

    @staticmethod
    def select(registry: ModelRegistry, request: RoutingRequest) -> ModelDescriptor:
        candidates = [m for m in registry.list_models() if request.required_capability in m.capabilities]
        if not candidates:
            raise NoCompatibleModelError(
                f"No registered model advertises capability {request.required_capability!r}."
            )

        tenant_ok = [m for m in candidates if m.is_tenant_allowed(request.tenant_id)]
        if not tenant_ok:
            raise NoCompatibleModelError(
                f"No model with capability {request.required_capability!r} is permitted for "
                f"tenant {request.tenant_id!r}."
            )

        # Residency/region constraint applied BEFORE cost.
        if request.allowed_regions is not None:
            region_ok = [m for m in tenant_ok if m.allowed_regions & request.allowed_regions]
            if not region_ok:
                raise ModelResidencyProhibitedError(
                    f"No compatible model is permitted in required region(s) {sorted(request.allowed_regions)}; "
                    f"refusing to relax the residency constraint."
                )
        else:
            region_ok = tenant_ok

        # Sensitivity/data-classification constraint applied BEFORE cost.
        sensitivity_ok = [m for m in region_ok if request.data_classification in m.allowed_data_classifications]
        if not sensitivity_ok:
            raise ModelSensitivityProhibitedError(
                f"No compatible model is approved to process {request.data_classification.value} data."
            )

        # Only now do health/approval and cost preference apply.
        healthy_approved = [
            m for m in sensitivity_ok
            if m.healthy and m.approval_status == ApprovalStatus.APPROVED
        ]
        if not healthy_approved:
            raise ModelUnavailableError(
                "Every model satisfying capability/residency/sensitivity constraints is "
                "currently unhealthy, unapproved, deprecated, or revoked."
            )

        if request.prefer_lowest_cost:
            healthy_approved.sort(key=lambda m: (m.relative_cost_score, m.model_id))
        else:
            healthy_approved.sort(key=lambda m: m.model_id)
        return healthy_approved[0]
