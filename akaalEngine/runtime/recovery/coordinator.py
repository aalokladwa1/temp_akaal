"""
akaalEngine.runtime.recovery.coordinator
=========================================
RuntimeRecoveryCoordinator consuming `DurabilityAuthority.inspect_recovery_state()`
to reconstruct active runtime task states after a restart or crash.
"""

from dataclasses import dataclass
import logging
from typing import Any, Dict, List, Optional

from akaalEngine.runtime.models.task import TaskState, TaskSnapshot

logger = logging.getLogger("akaalEngine.runtime.recovery")


@dataclass(frozen=True)
class RuntimeRecoveryPlan:
    """Plan for Runtime state reconstruction."""
    migration_id: str
    durable_checkpoint_id: Optional[str]
    fencing_epoch: int
    recoverable_tasks: List[str]
    terminal_tasks: List[str]
    reclaimable_claims: List[str]


class RuntimeRecoveryCoordinator:
    """
    RuntimeRecoveryCoordinator consuming Durability snapshots to discover surviving execution facts.
    """

    def __init__(self, durability_authority: Optional[Any] = None) -> None:
        self.durability_authority = durability_authority

    def evaluate_recovery(self, migration_id: str) -> RuntimeRecoveryPlan:
        durable_checkpoint_id = None
        epoch = 1
        recoverable: List[str] = []
        terminal: List[str] = []
        reclaimable: List[str] = []

        if self.durability_authority:
            try:
                snap = self.durability_authority.inspect_recovery_state(migration_id)
                if snap and snap.latest_checkpoint:
                    durable_checkpoint_id = snap.latest_checkpoint.checkpoint_id
                    epoch = snap.latest_checkpoint.fencing_epoch
                    logger.info(f"[RuntimeRecoveryCoordinator] Found durable checkpoint '{durable_checkpoint_id}' (epoch={epoch}) for migration '{migration_id}'.")

                if snap and snap.in_flight_operations:
                    for op in snap.in_flight_operations:
                        recoverable.append(op.operation_id)
            except Exception as exc:
                logger.warning(f"[RuntimeRecoveryCoordinator] Inspection error for '{migration_id}': {exc}")

        return RuntimeRecoveryPlan(
            migration_id=migration_id,
            durable_checkpoint_id=durable_checkpoint_id,
            fencing_epoch=epoch,
            recoverable_tasks=recoverable,
            terminal_tasks=terminal,
            reclaimable_claims=reclaimable,
        )
