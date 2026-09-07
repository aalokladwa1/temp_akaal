"""akaalEngine.intelligence.gateway.registry
=============================================
ModelDescriptor / ModelRegistry (P7C.4). Mirrors the fail-closed delegation shape
already used by akaalEngine.fabric.execution_site.registry.SiteRegistry: a
thread-safe registry that never self-grants trust -- APPROVED/health state is set
explicitly by an operator/governance action, never inferred by the model entry
itself claiming to be healthy or approved.
"""

from __future__ import annotations

import enum
import threading
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DEPRECATED = "DEPRECATED"
    REVOKED = "REVOKED"


class DataClassification(str, enum.Enum):
    """Sensitivity levels a model is permitted to process. Ordered least to most
    sensitive; a model's `allowed_data_classifications` must explicitly include a
    request's classification -- there is no implicit "higher approval covers
    lower" assumption, since some providers are approved for PUBLIC data only."""

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


@dataclass(frozen=True)
class ModelDescriptor:
    model_id: str
    provider: str
    model_family: str
    model_version: str
    capabilities: FrozenSet[str]
    allowed_regions: FrozenSet[str]
    allowed_data_classifications: FrozenSet[DataClassification]
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    healthy: bool = True
    is_local: bool = False
    allowed_tenants: Optional[FrozenSet[str]] = None
    deployment_id: Optional[str] = None
    context_limit_tokens: Optional[int] = None
    relative_cost_score: float = 1.0

    def __post_init__(self) -> None:
        if not self.model_id or not str(self.model_id).strip():
            raise ValueError("ModelDescriptor.model_id cannot be empty")
        object.__setattr__(self, "capabilities", frozenset(self.capabilities))
        object.__setattr__(self, "allowed_regions", frozenset(self.allowed_regions))
        object.__setattr__(self, "allowed_data_classifications", frozenset(self.allowed_data_classifications))
        if self.allowed_tenants is not None:
            object.__setattr__(self, "allowed_tenants", frozenset(self.allowed_tenants))

    def is_tenant_allowed(self, tenant_id: str) -> bool:
        return self.allowed_tenants is None or tenant_id in self.allowed_tenants

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "model_family": self.model_family,
            "model_version": self.model_version,
            "capabilities": sorted(self.capabilities),
            "allowed_regions": sorted(self.allowed_regions),
            "allowed_data_classifications": sorted(c.value for c in self.allowed_data_classifications),
            "approval_status": self.approval_status.value,
            "healthy": self.healthy,
            "is_local": self.is_local,
            "allowed_tenants": sorted(self.allowed_tenants) if self.allowed_tenants is not None else None,
            "deployment_id": self.deployment_id,
            "context_limit_tokens": self.context_limit_tokens,
            "relative_cost_score": self.relative_cost_score,
        }


class ModelRegistry:
    """Thread-safe registry of governed model endpoints. Registration and health/
    approval transitions are separate operations -- a caller cannot register a
    model that is simultaneously self-declared APPROVED and healthy without an
    explicit governance action, exactly mirroring how a new connector provider
    strategy must still pass through explicit trust verification elsewhere."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._models: Dict[str, ModelDescriptor] = {}

    def register(self, descriptor: ModelDescriptor) -> None:
        with self._lock:
            self._models[descriptor.model_id] = descriptor

    def get(self, model_id: str) -> Optional[ModelDescriptor]:
        with self._lock:
            return self._models.get(model_id)

    def list_models(self) -> List[ModelDescriptor]:
        with self._lock:
            return list(self._models.values())

    def set_health(self, model_id: str, healthy: bool) -> None:
        with self._lock:
            existing = self._models.get(model_id)
            if existing is None:
                return
            import dataclasses as _dc

            self._models[model_id] = _dc.replace(existing, healthy=healthy)

    def set_approval_status(self, model_id: str, status: ApprovalStatus) -> None:
        with self._lock:
            existing = self._models.get(model_id)
            if existing is None:
                return
            import dataclasses as _dc

            self._models[model_id] = _dc.replace(existing, approval_status=status)
