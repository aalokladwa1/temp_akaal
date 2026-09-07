"""
akaalEngine.fabric.gitops.models
====================================
P7B.30 -- GitOps & Fleet Lifecycle data model.

FORBIDDEN GITOPS STATE LAW (P7B Group-3 directive Section 14, enforced STRUCTURALLY, not
merely documented): `FleetDesiredState` has no field, anywhere, for live migration runtime
state, mutable ExecutionPlan runtime truth, checkpoint state, CDC positions, validation
state, approval truth, plaintext secrets, private keys, cloud tokens, active lease,
fencing authority, or ownership state. This is deliberate -- there is no way to construct
a `FleetDesiredState` that carries any of those, because the dataclass simply has no slot
for them. `config` (the one open-ended field) additionally gets a defense-in-depth scan
for secret/runtime-state-shaped key names at construction time, so even a caller trying to
smuggle such data into the one flexible field is refused outright.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Mapping, Tuple


class GitOpsValidationError(ValueError):
    pass


class ReconciliationState(str, Enum):
    IN_SYNC = "IN_SYNC"
    PENDING = "PENDING"
    DRIFTED = "DRIFTED"
    FAILED = "FAILED"
    INCOMPATIBLE = "INCOMPATIBLE"
    PARTIALLY_APPLIED = "PARTIALLY_APPLIED"


# Defense-in-depth only (the real defense is structural: these dimensions have no
# dedicated field on FleetDesiredState at all). A key or value containing any of these
# substrings (case-insensitive) is refused -- a legitimate GitOps-managed runtime/version/
# deployment config key never needs to look like this.
_FORBIDDEN_CONFIG_SUBSTRINGS: Tuple[str, ...] = (
    "password", "secret", "token", "private_key", "privatekey", "credential",
    "checkpoint", "cdc_position", "cdcposition", "lease_id", "fencing_generation",
    "ownership_key", "approval", "api_key", "apikey",
)


def _scan_config_for_forbidden_content(config: Mapping[str, str]) -> None:
    for key, value in config.items():
        haystack = f"{key} {value}".lower()
        for banned in _FORBIDDEN_CONFIG_SUBSTRINGS:
            if banned in haystack:
                raise GitOpsValidationError(
                    f"FleetDesiredState.config entry {key!r} looks secret/runtime-state-"
                    f"shaped (matched {banned!r}); GitOps desired state must never carry "
                    f"secrets or live migration/ownership/fencing truth."
                )


@dataclass(frozen=True)
class FleetDesiredState:
    """
    Declarative GitOps-managed desired state for fleet/runtime/deployment configuration
    ONLY. `approved_by` is attribution (who authored this revision) -- it is NEVER itself
    an authorization grant; applying a FleetDesiredState still goes through whatever
    canonical authorization/Kubernetes-RBAC/Helm/Terraform apply-time checks already
    govern infrastructure changes, unchanged by this module.
    """

    revision_id: str
    target_runtime_version: str
    target_worker_pool_size: int
    config: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    approved_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.revision_id or not self.revision_id.strip():
            raise GitOpsValidationError("FleetDesiredState.revision_id must be non-empty.")
        if not self.target_runtime_version or not self.target_runtime_version.strip():
            raise GitOpsValidationError("FleetDesiredState.target_runtime_version must be non-empty.")
        if self.target_worker_pool_size < 0:
            raise GitOpsValidationError("FleetDesiredState.target_worker_pool_size must be >= 0.")
        if not isinstance(self.config, MappingProxyType):
            object.__setattr__(self, "config", MappingProxyType(dict(self.config)))
        _scan_config_for_forbidden_content(self.config)
        if not self.approved_by or not self.approved_by.strip():
            raise GitOpsValidationError(
                "FleetDesiredState.approved_by must be non-empty -- every desired-state "
                "revision must be attributable to a specific author, never anonymous."
            )


@dataclass(frozen=True)
class ReconciliationReport:
    revision_id: str
    state: ReconciliationState
    active_worker_count: int
    at_target_version_count: int
    other_version_count: int
    reasons: Tuple[str, ...] = field(default_factory=tuple)

    def is_settled(self) -> bool:
        return self.state == ReconciliationState.IN_SYNC
