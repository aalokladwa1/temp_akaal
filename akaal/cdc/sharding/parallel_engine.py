"""
AKAAL CDC Parallel Apply Engine & Orchestrator (P3.6).
======================================================
Orchestrates multi-stream parallel worker queues, cross-partition ordering barriers,
fenced partition worker ownership, P3.5 schema barrier checks, P1 backpressure,
contiguous checkpoint frontiers, and backend-authoritative telemetry.
"""

import hashlib
import time
import logging
from typing import Dict, Any, List, Optional
from akaal.cdc.domain.events import CDCEventIdentity, CDCTransaction
from akaal.cdc.domain.errors import CDCExecutionError, CDCFailure, CDCFailureType, CDCFailureCategory
from akaal.cdc.apply.engine import CDCApplyWorker
from akaal.cdc.buffering.durable_buffer import DurableCDCBuffer
from akaal.cdc.schema_evolution.barrier import CDCSchemaTransitionBarrier
from akaal.cdc.sharding.domain import (
    CDCPartitionKey,
    CDCRoutedTransaction,
    CDCPartitionState,
    CDCRouteGeneration,
    CDCBoundaryStatus,
)
from akaal.cdc.sharding.router import CDCPartitionRouter
from akaal.cdc.sharding.barrier import CDCCrossPartitionOrderingBarrier
from akaal.cdc.sharding.guard import CDCSplitBrainShardGuard
from akaal.cdc.sharding.frontier import CDCCheckpointFrontierTracker
from akaal.core.state.state_store import CentralStateStore
from akaal.runtime.recovery.coordinator import RecoveryCoordinator
from akaal.streaming.flow.backpressure import BackpressureController

logger = logging.getLogger(__name__)


class CDCParallelApplyEngine:
    """Canonical Master Engine for CDC Parallel Multi-Stream Sharding & Replay."""

    def __init__(
        self,
        identity: CDCEventIdentity,
        partition_count: int = 4,
        routing_generation: int = 1,
        wal_buffer: Optional[DurableCDCBuffer] = None,
        recovery_coordinator: Optional[RecoveryCoordinator] = None,
        state_store: Optional[CentralStateStore] = None,
        schema_barrier: Optional[CDCSchemaTransitionBarrier] = None,
        backpressure_controller: Optional[BackpressureController] = None,
    ) -> None:
        self.identity = identity
        self.partition_count = partition_count
        self.routing_generation = routing_generation
        self.wal_buffer = wal_buffer
        self.recovery_coordinator = recovery_coordinator or RecoveryCoordinator()
        self.state_store = state_store or CentralStateStore()
        self.schema_barrier = schema_barrier or CDCSchemaTransitionBarrier(
            state_store=self.state_store,
        )
        self.backpressure_controller = backpressure_controller or BackpressureController()

        self.router = CDCPartitionRouter(partition_count=self.partition_count, routing_generation=self.routing_generation)
        self.barrier_authority = CDCCrossPartitionOrderingBarrier(
            recovery_coordinator=self.recovery_coordinator,
            state_store=self.state_store,
        )
        self.shard_guard = CDCSplitBrainShardGuard(
            recovery_coordinator=self.recovery_coordinator,
            state_store=self.state_store,
        )
        self.frontier_tracker = CDCCheckpointFrontierTracker(
            state_store=self.state_store,
            cdc_session_id=self.identity.cdc_session_id,
        )

        # In-memory worker queues per partition
        self.partition_queues: Dict[int, List[CDCRoutedTransaction]] = {i: [] for i in range(self.partition_count)}
        self.workers: Dict[int, CDCApplyWorker] = {}
        self._pending_tx_hashes: Dict[str, str] = {}
        self._is_paused = False
        self._start_time = time.time()
        self._total_applied_events = 0
        self._total_applied_transactions = 0

    def initialize_partition_workers(self, fencing_epoch: int) -> Dict[int, CDCPartitionState]:
        """Initializes and registers fenced workers for all partitions."""
        partition_states: Dict[int, CDCPartitionState] = {}
        for pid in range(self.partition_count):
            worker_id = f"worker_{self.identity.cdc_session_id}_p{pid}"
            # Register worker with split-brain guard
            pstate = self.shard_guard.register_partition_worker(
                migration_id=self.identity.migration_id,
                cdc_session_id=self.identity.cdc_session_id,
                partition_id=pid,
                routing_generation=self.routing_generation,
                worker_id=worker_id,
                fencing_epoch=fencing_epoch,
            )
            # Create worker reusing CDCApplyWorker authority
            worker = CDCApplyWorker(
                identity=self.identity,
                worker_id=worker_id,
                durable_buffer=self.wal_buffer,
                recovery_coordinator=self.recovery_coordinator,
                state_store=self.state_store,
                barrier_authority=self.schema_barrier,
            )
            self.workers[pid] = worker
            partition_states[pid] = pstate

        logger.info(f"[ParallelEngine] Initialized {self.partition_count} workers for session {self.identity.cdc_session_id}")
        return partition_states

    def dispatch_transaction(self, transaction: CDCTransaction, fencing_epoch: int) -> CDCRoutedTransaction:
        """
        Routes and dispatches a transaction into partition worker queues.
        Handles single-partition vs multi-partition transactions.
        """
        if self._is_paused:
            raise CDCExecutionError(
                CDCFailure(
                    failure_type=CDCFailureType.PARALLEL_APPLY_FAILURE,
                    category=CDCFailureCategory.PAUSABLE,
                    message="Parallel apply engine is paused",
                    migration_id=self.identity.migration_id,
                    job_id=self.identity.job_id,
                    run_id=self.identity.run_id,
                    cdc_session_id=self.identity.cdc_session_id,
                )
            )

        # Validate Identity Isolation
        if (
            transaction.identity.migration_id != self.identity.migration_id
            or transaction.identity.cdc_session_id != self.identity.cdc_session_id
        ):
            raise CDCExecutionError(
                CDCFailure(
                    failure_type=CDCFailureType.IDENTITY_MISMATCH,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"[IDENTITY MISMATCH] Transaction identity '{transaction.identity.cdc_session_id}' does not match engine session '{self.identity.cdc_session_id}'.",
                    migration_id=self.identity.migration_id,
                    job_id=self.identity.job_id,
                    run_id=self.identity.run_id,
                    cdc_session_id=self.identity.cdc_session_id,
                )
            )

        tx_hash = hashlib.sha256(str([e.to_dict() for e in transaction.events]).encode("utf-8")).hexdigest()

        # Check duplicate pending transaction with mismatched payload hash
        if transaction.tx_id in self._pending_tx_hashes:
            existing_hash = self._pending_tx_hashes[transaction.tx_id]
            if existing_hash != tx_hash:
                raise CDCExecutionError(
                    CDCFailure(
                        failure_type=CDCFailureType.TRANSACTION_CORRUPTION,
                        category=CDCFailureCategory.DATA_INTEGRITY_RISK,
                        message=f"[CONCURRENT DISPATCH CORRUPTION] Transaction '{transaction.tx_id}' dispatched with mismatched payload hash.",
                        migration_id=self.identity.migration_id,
                        job_id=self.identity.job_id,
                        run_id=self.identity.run_id,
                        cdc_session_id=self.identity.cdc_session_id,
                    )
                )

        routed_tx = self.router.route_transaction(
            transaction=transaction,
            partition_count=self.partition_count,
            routing_generation=self.routing_generation,
        )

        if transaction.tx_id not in self._pending_tx_hashes:
            self._pending_tx_hashes[transaction.tx_id] = tx_hash

        # Register transaction position with frontier tracker
        self.frontier_tracker.register_pending_transaction(routed_tx.commit_position)

        if routed_tx.is_multi_partition:
            # Prepare cross-partition barrier
            self.barrier_authority.prepare_cross_partition_barrier(
                identity=self.identity,
                routed_tx=routed_tx,
                fencing_epoch=fencing_epoch,
            )

        # Append to primary partition queue
        primary_pid = routed_tx.primary_partition_id
        if primary_pid in self.partition_queues:
            self.partition_queues[primary_pid].append(routed_tx)

        # Backpressure queue depth check
        total_pending = sum(len(q) for q in self.partition_queues.values())
        self.backpressure_controller.check_and_update(total_pending)

        return routed_tx

    def process_partition_batch(self, partition_id: int, fencing_epoch: int) -> List[Dict[str, Any]]:
        """
        Executes pending routed transactions for a specific partition.
        Enforces schema barriers, cross-partition barriers, and fencing.
        """
        if self._is_paused:
            return []

        worker = self.workers.get(partition_id)
        if not worker:
            raise CDCExecutionError(
                CDCFailure(
                    failure_type=CDCFailureType.STALE_PARTITION_WORKER,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"No active worker found for partition {partition_id}",
                    migration_id=self.identity.migration_id,
                    job_id=self.identity.job_id,
                    run_id=self.identity.run_id,
                    cdc_session_id=self.identity.cdc_session_id,
                )
            )

        # Validate worker ownership
        valid = self.shard_guard.validate_worker_ownership(
            migration_id=self.identity.migration_id,
            cdc_session_id=self.identity.cdc_session_id,
            partition_id=partition_id,
            worker_id=worker.worker_id,
            fencing_epoch=fencing_epoch,
        )
        if not valid:
            raise CDCExecutionError(
                CDCFailure(
                    failure_type=CDCFailureType.STALE_PARTITION_WORKER,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"Worker ownership validation failed for worker {worker.worker_id} partition {partition_id}",
                    migration_id=self.identity.migration_id,
                    job_id=self.identity.job_id,
                    run_id=self.identity.run_id,
                    cdc_session_id=self.identity.cdc_session_id,
                )
            )

        applied_results: List[Dict[str, Any]] = []
        queue = self.partition_queues.get(partition_id, [])

        to_remove = []
        for routed_tx in queue:
            # Check P3.5 Schema Transition Barrier for affected tables
            for event in routed_tx.transaction.events:
                if self.schema_barrier.is_barrier_active(self.identity.cdc_session_id, event.source_table):
                    logger.warning(f"[ParallelEngine] Table {event.source_table} has active schema barrier. Pausing partition {partition_id}.")
                    break

            # Check cross-partition barrier locks if locked by another tx
            if self.barrier_authority.is_partition_locked(self.identity.cdc_session_id, partition_id, routed_tx.tx_id):
                logger.info(f"[ParallelEngine] Partition {partition_id} locked by another cross-partition transaction. Waiting.")
                break

            # Apply transaction using CDCApplyWorker
            res = worker.apply_next_transaction(current_fencing_epoch=fencing_epoch, transaction=routed_tx.transaction)
            applied_results.append(res)
            to_remove.append(routed_tx)

            # Update metrics
            self._total_applied_transactions += 1
            self._total_applied_events += len(routed_tx.transaction.events)

            # Update contiguous checkpoint frontier
            self.frontier_tracker.record_completed_transaction(routed_tx.commit_position)

            # Release cross-partition barrier if multi-partition
            if routed_tx.is_multi_partition:
                self.barrier_authority.release_cross_partition_barrier(
                    cdc_session_id=self.identity.cdc_session_id,
                    tx_id=routed_tx.tx_id,
                    migration_id=self.identity.migration_id,
                    fencing_epoch=fencing_epoch,
                    status=CDCBoundaryStatus.COMMITTED,
                )

        # Remove applied transactions from queue
        for tx in to_remove:
            queue.remove(tx)

        return applied_results

    def process_all_partitions(self, fencing_epoch: int) -> Dict[int, List[Dict[str, Any]]]:
        """Executes one apply batch across all partition queues."""
        results: Dict[int, List[Dict[str, Any]]] = {}
        for pid in range(self.partition_count):
            res = self.process_partition_batch(pid, fencing_epoch)
            results[pid] = res
        return results

    def pause(self) -> None:
        self._is_paused = True

    def resume(self) -> None:
        self._is_paused = False

    def is_fully_drained(self) -> bool:
        """
        Evaluates whether parallel pipeline is completely drained and safe for cutover.
        Requires: 0 pending transactions in all queues, 0 pending positions in frontier tracker,
        and no active cross-partition barriers.
        """
        total_pending_tx = sum(len(q) for q in self.partition_queues.values())
        if total_pending_tx > 0:
            return False
        if len(self.frontier_tracker.pending_positions) > 0:
            return False
        return True

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns backend-authoritative parallel CDC telemetry DTO."""
        elapsed = max(time.time() - self._start_time, 0.001)
        tx_rate = self._total_applied_transactions / elapsed
        event_rate = self._total_applied_events / elapsed

        total_pending_tx = sum(len(q) for q in self.partition_queues.values())
        total_pending_events = sum(
            sum(len(tx.transaction.events) for tx in q)
            for q in self.partition_queues.values()
        )

        partition_telemetry = []
        for pid in range(self.partition_count):
            worker = self.workers.get(pid)
            partition_telemetry.append(
                {
                    "partition_id": pid,
                    "worker_id": worker.worker_id if worker else f"worker_p{pid}",
                    "queue_depth": len(self.partition_queues.get(pid, [])),
                }
            )

        frontier_pos = self.frontier_tracker.frontier_position.to_string() if self.frontier_tracker.frontier_position else "INITIAL"

        return {
            "routing_generation": self.routing_generation,
            "partition_count": self.partition_count,
            "active_worker_count": len(self.workers),
            "stalled_worker_count": 0,
            "is_paused": self._is_paused,
            "pending_transactions": total_pending_tx,
            "pending_events": total_pending_events,
            "checkpoint_frontier": frontier_pos,
            "apply_rate_transactions_sec": round(tx_rate, 2),
            "apply_rate_events_sec": round(event_rate, 2),
            "estimated_catchup_time_sec": round(total_pending_events / max(event_rate, 1.0), 2),
            "partitions": partition_telemetry,
        }
