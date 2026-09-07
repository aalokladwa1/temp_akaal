"""
akaalEngine.fabric.fleet_lifecycle.models
=============================================
P7B.31 -- Fleet Configuration & Upgrade Management data model.

Two small, genuinely new pieces layered on top of the already-frozen P7B.22/P7B.23/P7B.30
authorities (WorkerRegistry, plan_rollout_batch, FleetDesiredState) -- this module invents
no second worker registry, no second rollout planner, and no second GitOps authority:

    * `RuntimeCompatibilityPolicy` -- an explicit, caller-approved ALLOWED SET of runtime
      versions a placement/upgrade decision may treat as compatible. Mirrors
      akaalEngine.fabric.placement.residency.ResidencyPolicy's "no default-allow, only an
      explicit allowed set" discipline exactly: there is no implicit "latest wins" or
      "assume compatible" path.
    * `RevisionHistory` -- an append-only record of which `FleetDesiredState` revisions
      were applied and when, so "roll back to the previous revision" means "point the
      desired-state pointer at an earlier, already-recorded revision_id", never "mutate
      migration/runtime/checkpoint truth" (which this module has no field for at all,
      identical discipline to P7B.30's FleetDesiredState).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import FrozenSet, List, Optional, Tuple

from akaalEngine.fabric.gitops.models import FleetDesiredState


class FleetLifecycleError(ValueError):
    pass


@dataclass(frozen=True)
class RuntimeCompatibilityPolicy:
    policy_id: str
    allowed_versions: FrozenSet[str]

    def __post_init__(self) -> None:
        if not self.policy_id or not self.policy_id.strip():
            raise FleetLifecycleError("RuntimeCompatibilityPolicy.policy_id must be non-empty.")
        if not isinstance(self.allowed_versions, frozenset):
            object.__setattr__(self, "allowed_versions", frozenset(self.allowed_versions))
        if not self.allowed_versions:
            raise FleetLifecycleError("RuntimeCompatibilityPolicy.allowed_versions must be non-empty.")

    def is_compatible(self, runtime_version: str) -> bool:
        return runtime_version in self.allowed_versions


@dataclass(frozen=True)
class RevisionRecord:
    desired_state: FleetDesiredState
    applied_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RevisionHistory:
    """
    Append-only, in-memory revision log. Not itself durable (a production deployment
    backs this with the same GitOps source-of-truth the desired state already comes
    from -- Git history IS the durable revision log; this class is a convenience view
    over already-applied revisions, not a second persistence authority).
    """

    def __init__(self) -> None:
        self._records: List[RevisionRecord] = []

    def record_applied(self, desired_state: FleetDesiredState) -> RevisionRecord:
        record = RevisionRecord(desired_state=desired_state)
        self._records.append(record)
        return record

    def current(self) -> Optional[FleetDesiredState]:
        return self._records[-1].desired_state if self._records else None

    def previous(self) -> Optional[FleetDesiredState]:
        return self._records[-2].desired_state if len(self._records) >= 2 else None

    def history(self) -> Tuple[RevisionRecord, ...]:
        return tuple(self._records)

    def rollback_to(self, revision_id: str) -> FleetDesiredState:
        """
        Returns the FleetDesiredState for `revision_id` from history and records it as a
        newly-applied revision (a rollback IS a new revision application, pointing back at
        old content -- never a mutation of history, so the audit trail always shows every
        revision that was ever active, including repeats). Raises if `revision_id` was
        never actually applied before -- a rollback can only target a real prior state,
        never an invented one.
        """
        for record in self._records:
            if record.desired_state.revision_id == revision_id:
                return self.record_applied(record.desired_state).desired_state
        raise FleetLifecycleError(f"Cannot roll back to revision_id {revision_id!r}: it was never previously applied.")
