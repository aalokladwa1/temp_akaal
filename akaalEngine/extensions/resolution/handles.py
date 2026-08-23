"""
akaalEngine.extensions.resolution.handles
=========================================
Internal immutable handles returned upon successful strategy resolution.
Carries the strategy factory/instance, lease token, effective capability truth, and generation metadata.
Must NEVER be serialized directly through EngineGateway.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from akaalEngine.extensions.lifecycle.leases import HandleLeaseTracker, LeaseToken, default_lease_tracker
from akaalEngine.extensions.models.capability import CapabilityTruth
from akaalEngine.extensions.models.identity import (
    AuthorityId,
    ExtensionId,
    ProviderId,
    RegistryGeneration,
    StrategyId,
)


@dataclass(frozen=True)
class ResolvedStrategyHandle:
    """
    Internal Engine handle representing a leased strategy execution instance.
    Includes lifecycle lease tracking and context management.
    """
    extension_id: ExtensionId
    provider_id: ProviderId
    authority_id: AuthorityId
    strategy_id: StrategyId
    implementation_version: str
    generation: RegistryGeneration
    strategy_instance: Any
    lease_token: LeaseToken
    capabilities: Mapping[str, CapabilityTruth] = field(default_factory=dict)
    _lease_tracker: HandleLeaseTracker = field(default=default_lease_tracker, repr=False)

    def release(self) -> bool:
        """Releases the underlying handle lease back to the tracker."""
        return self._lease_tracker.release_lease(self.lease_token)

    def is_capability_supported(self, capability_name: str) -> bool:
        cap = self.capabilities.get(capability_name.strip().upper())
        return cap.is_supported if cap else False

    def __enter__(self) -> ResolvedStrategyHandle:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.release()
