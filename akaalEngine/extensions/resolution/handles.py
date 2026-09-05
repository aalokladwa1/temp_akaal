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

from akaalEngine.extensions.errors.taxonomy import CapabilityNotSupportedError
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

    def require_capability(self, capability_name: str) -> CapabilityTruth:
        """
        Fail-closed capability gate: raises CapabilityNotSupportedError unless the resolved
        strategy has an affirmatively supported (and dependency-satisfied) declaration for
        `capability_name`. A missing declaration is treated identically to an explicit
        is_supported=False -- silence is never treated as support.
        """
        key = capability_name.strip().upper()
        cap = self.capabilities.get(key)
        if cap is None or not cap.is_supported:
            diagnostic = cap.diagnostic if cap is not None else "no capability declaration present"
            raise CapabilityNotSupportedError(
                f"Strategy '{self.strategy_id}' (provider '{self.provider_id}', authority "
                f"'{self.authority_id}') does not support capability '{key}': {diagnostic}.",
                details={
                    "provider_id": str(self.provider_id),
                    "authority_id": str(self.authority_id),
                    "strategy_id": str(self.strategy_id),
                    "capability_name": key,
                },
            )
        return cap

    def __enter__(self) -> ResolvedStrategyHandle:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.release()
