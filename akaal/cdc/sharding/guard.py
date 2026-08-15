"""
AKAAL Split-Brain Shard Guard & Worker Fencing Authority (P3.6).
================================================================
Guarantees single worker ownership per partition generation.
Fences stale worker instances and manages safe rebalancing lifecycles.
Integrates directly with RecoveryCoordinator for fencing epoch management.
"""

import logging
from typing import Dict, Any, List, Optional
from akaal.cdc.domain.errors import CDCExecutionError, CDCFailure, CDCFailureType, CDCFailureCategory
from akaal.cdc.sharding.domain import CDCPartitionState, CDCRouteGeneration
from akaal.core.state.state_store import CentralStateStore
from akaal.runtime.recovery.coordinator import RecoveryCoordinator

logger = logging.getLogger(__name__)


class CDCSplitBrainShardGuard:
    """Canonical Split-Brain Shard Guard & Worker Fencing Authority."""

    def __init__(
        self,
        recovery_coordinator: Optional[RecoveryCoordinator] = None,
        state_store: Optional[CentralStateStore] = None,
    ) -> None:
        self.recovery_coordinator = recovery_coordinator or RecoveryCoordinator()
        self.state_store = state_store or CentralStateStore()

    def _get_partition_state_key(self, cdc_session_id: str, partition_id: int) -> str:
        return f"cdc_partition_state_{cdc_session_id}_{partition_id}"

    def register_partition_worker(
        self,
        migration_id: str,
        cdc_session_id: str,
        partition_id: int,
        routing_generation: int,
        worker_id: str,
        fencing_epoch: int,
    ) -> CDCPartitionState:
        """Registers a worker as authoritative owner of a partition slot."""
        valid_epoch = self.recovery_coordinator.validate_fencing_token(migration_id, fencing_epoch)
        if not valid_epoch:
            raise CDCExecutionError(
                CDCFailure(
                    failure_type=CDCFailureType.STALE_PARTITION_WORKER,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"Stale fencing epoch {fencing_epoch} rejected for worker {worker_id} partition {partition_id}",
                    migration_id=migration_id,
                    job_id="",
                    run_id="",
                    cdc_session_id=cdc_session_id,
                )
            )

        key = self._get_partition_state_key(cdc_session_id, partition_id)
        existing = self.state_store.get_state(key, category="partition_ownership")

        if existing:
            current_state = CDCPartitionState.from_dict(existing)
            if current_state.fencing_epoch > fencing_epoch:
                raise CDCExecutionError(
                    CDCFailure(
                        failure_type=CDCFailureType.PARTITION_OWNERSHIP_CONFLICT,
                        category=CDCFailureCategory.BLOCKING,
                        message=f"Ownership conflict: partition {partition_id} owned by epoch {current_state.fencing_epoch} > candidate {fencing_epoch}",
                        migration_id=migration_id,
                        job_id="",
                        run_id="",
                        cdc_session_id=cdc_session_id,
                    )
                )

        pstate = CDCPartitionState(
            partition_id=partition_id,
            routing_generation=routing_generation,
            owner_worker_id=worker_id,
            fencing_epoch=fencing_epoch,
            rebalance_state="STABLE",
        )
        self.state_store.set_state(key, pstate.to_dict(), category="partition_ownership")
        logger.info(f"[ShardGuard] Worker {worker_id} claimed partition {partition_id} (gen={routing_generation}, epoch={fencing_epoch})")
        return pstate

    def validate_worker_ownership(
        self,
        migration_id: str,
        cdc_session_id: str,
        partition_id: int,
        worker_id: str,
        fencing_epoch: int,
    ) -> bool:
        """Verifies that worker_id holds authoritative ownership of partition_id under active fencing_epoch."""
        valid_epoch = self.recovery_coordinator.validate_fencing_token(migration_id, fencing_epoch)
        if not valid_epoch:
            return False

        key = self._get_partition_state_key(cdc_session_id, partition_id)
        existing = self.state_store.get_state(key, category="partition_ownership")
        if not existing:
            return False

        pstate = CDCPartitionState.from_dict(existing)
        if pstate.owner_worker_id != worker_id or pstate.fencing_epoch != fencing_epoch:
            return False
        return True

    def initiate_rebalance(
        self,
        migration_id: str,
        cdc_session_id: str,
        new_partition_count: int,
        fencing_epoch: int,
    ) -> CDCRouteGeneration:
        """Initiates safe rebalancing lifecycle, bumping routing generation."""
        valid_epoch = self.recovery_coordinator.validate_fencing_token(migration_id, fencing_epoch)
        if not valid_epoch:
            raise CDCExecutionError(
                CDCFailure(
                    failure_type=CDCFailureType.STALE_PARTITION_WORKER,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"Stale fencing epoch {fencing_epoch} rejected for rebalance initiation",
                    migration_id=migration_id,
                    job_id="",
                    run_id="",
                    cdc_session_id=cdc_session_id,
                )
            )

        gen_key = f"cdc_route_gen_{cdc_session_id}"
        current_gen_data = self.state_store.get_state(gen_key, category="route_generation")
        current_gen = current_gen_data.get("routing_generation", 0) if current_gen_data else 0
        new_gen_num = current_gen + 1

        route_gen = CDCRouteGeneration(
            routing_generation=new_gen_num,
            partition_count=new_partition_count,
            cdc_session_id=cdc_session_id,
            status="REBALANCING",
        )
        self.state_store.set_state(gen_key, route_gen.to_dict(), category="route_generation")
        logger.info(f"[ShardGuard] Initiated rebalance to gen={new_gen_num} with {new_partition_count} partitions")
        return route_gen

    def complete_rebalance(
        self,
        migration_id: str,
        cdc_session_id: str,
        routing_generation: int,
        fencing_epoch: int,
    ) -> bool:
        """Completes rebalancing, marking routing generation ACTIVE."""
        valid_epoch = self.recovery_coordinator.validate_fencing_token(migration_id, fencing_epoch)
        if not valid_epoch:
            return False

        gen_key = f"cdc_route_gen_{cdc_session_id}"
        current_gen_data = self.state_store.get_state(gen_key, category="route_generation")
        if current_gen_data and current_gen_data.get("routing_generation") == routing_generation:
            current_gen_data["status"] = "ACTIVE"
            self.state_store.set_state(gen_key, current_gen_data, category="route_generation")
            return True
        return False
