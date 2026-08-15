"""
AKAAL Cross-Partition Ordering Barrier (P3.6).
============================================================
Coordinates multi-partition transactions across worker queues.
Prevents partial target transaction commits and out-of-order execution across partitions.
Integrates with RecoveryCoordinator for fencing epoch validation and persists to CentralStateStore.
"""

import logging
from typing import Dict, Any, List, Optional
from akaal.cdc.domain.events import CDCEventIdentity
from akaal.cdc.domain.errors import CDCExecutionError, CDCFailure, CDCFailureType, CDCFailureCategory
from akaal.cdc.sharding.domain import CDCRoutedTransaction, CDCBoundaryStatus
from akaal.core.state.state_store import CentralStateStore
from akaal.runtime.recovery.coordinator import RecoveryCoordinator

logger = logging.getLogger(__name__)


class CDCCrossPartitionOrderingBarrier:
    """Canonical Cross-Partition Ordering Barrier Authority."""

    def __init__(
        self,
        recovery_coordinator: Optional[RecoveryCoordinator] = None,
        state_store: Optional[CentralStateStore] = None,
    ) -> None:
        self.recovery_coordinator = recovery_coordinator or RecoveryCoordinator()
        self.state_store = state_store or CentralStateStore()

    def _get_barrier_key(self, cdc_session_id: str, tx_id: str) -> str:
        return f"cdc_cross_barrier_{cdc_session_id}_{tx_id}"

    def prepare_cross_partition_barrier(
        self,
        identity: CDCEventIdentity,
        routed_tx: CDCRoutedTransaction,
        fencing_epoch: int,
    ) -> Dict[str, Any]:
        """
        Reserves all target partitions for a multi-partition transaction under fencing_epoch control.
        Persists barrier to CentralStateStore.
        """
        # Validate fencing epoch
        valid_epoch = self.recovery_coordinator.validate_fencing_token(identity.migration_id, fencing_epoch)
        if not valid_epoch:
            raise CDCExecutionError(
                CDCFailure(
                    failure_type=CDCFailureType.STALE_PARTITION_WORKER,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"Stale fencing epoch {fencing_epoch} rejected for cross-partition barrier prepare",
                    migration_id=identity.migration_id,
                    job_id=identity.job_id,
                    run_id=identity.run_id,
                    cdc_session_id=identity.cdc_session_id,
                )
            )

        if not routed_tx.is_multi_partition:
            return {"barrier_active": False, "status": "SINGLE_PARTITION"}

        key = self._get_barrier_key(identity.cdc_session_id, routed_tx.tx_id)
        existing = self.state_store.get_state(key, category="cross_partition_barrier")
        if existing and existing.get("status") in [CDCBoundaryStatus.RESERVED.value, CDCBoundaryStatus.IN_PROGRESS.value]:
            # Already active
            return existing

        barrier_record = {
            "identity": identity.to_dict(),
            "tx_id": routed_tx.tx_id,
            "partition_ids": routed_tx.partition_ids,
            "routing_generation": routed_tx.routing_generation,
            "fencing_epoch": fencing_epoch,
            "status": CDCBoundaryStatus.RESERVED.value,
        }
        self.state_store.set_state(key, barrier_record, category="cross_partition_barrier")

        # Record active partition locks in state store
        for pid in routed_tx.partition_ids:
            part_lock_key = f"cdc_partition_lock_{identity.cdc_session_id}_{pid}"
            self.state_store.set_state(part_lock_key, {"tx_id": routed_tx.tx_id, "fencing_epoch": fencing_epoch}, category="partition_lock")

        logger.info(
            f"[CrossPartitionBarrier] Reserved partitions {routed_tx.partition_ids} for tx={routed_tx.tx_id} epoch={fencing_epoch}"
        )
        return barrier_record

    def is_partition_locked(self, cdc_session_id: str, partition_id: int, tx_id: str) -> bool:
        """Returns True if the partition is locked by a multi-partition transaction other than tx_id."""
        part_lock_key = f"cdc_partition_lock_{cdc_session_id}_{partition_id}"
        lock = self.state_store.get_state(part_lock_key, category="partition_lock")
        if lock and lock.get("tx_id") != tx_id:
            return True
        return False

    def release_cross_partition_barrier(
        self,
        cdc_session_id: str,
        tx_id: str,
        migration_id: str,
        fencing_epoch: int,
        status: CDCBoundaryStatus = CDCBoundaryStatus.COMMITTED,
    ) -> bool:
        """Releases all partition locks for tx_id after terminal commit or rollback."""
        valid_epoch = self.recovery_coordinator.validate_fencing_token(migration_id, fencing_epoch)
        if not valid_epoch:
            raise CDCExecutionError(
                CDCFailure(
                    failure_type=CDCFailureType.STALE_PARTITION_WORKER,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"Stale fencing epoch {fencing_epoch} rejected for cross-partition barrier release",
                    migration_id=migration_id,
                    job_id="",
                    run_id="",
                    cdc_session_id=cdc_session_id,
                )
            )

        key = self._get_barrier_key(cdc_session_id, tx_id)
        existing = self.state_store.get_state(key, category="cross_partition_barrier")
        if not existing:
            return True

        partition_ids = existing.get("partition_ids", [])
        for pid in partition_ids:
            part_lock_key = f"cdc_partition_lock_{cdc_session_id}_{pid}"
            self.state_store.set_state(part_lock_key, None, category="partition_lock")

        existing["status"] = status.value
        self.state_store.set_state(key, existing, category="cross_partition_barrier")
        logger.info(f"[CrossPartitionBarrier] Released partitions {partition_ids} for tx={tx_id} status={status.value}")
        return True
