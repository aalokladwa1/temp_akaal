"""
AKAAL Master Transaction Ordering & Causality Coordinator (P3.7).
===================================================================
Master orchestrator integrating causality graph engine, replay eligibility engine,
P3.6 parallel apply engine, P3.5 schema barriers, P1 backpressure, and cutover gates.
"""

import logging
from typing import Dict, Any, List, Optional
from akaal.cdc.domain.events import CDCEventIdentity, CDCTransaction
from akaal.cdc.domain.errors import CDCExecutionError, CDCFailure, CDCFailureType, CDCFailureCategory
from akaal.cdc.ordering.domain import (
    CDCReplayEligibility,
    CDCOrderingDecision,
)
from akaal.cdc.ordering.causality import CDCCausalityGraphEngine
from akaal.cdc.ordering.eligibility import CDCReplayEligibilityEngine
from akaal.cdc.sharding.parallel_engine import CDCParallelApplyEngine
from akaal.cdc.schema_evolution.barrier import CDCSchemaTransitionBarrier
from akaal.core.state.state_store import CentralStateStore
from akaal.runtime.recovery.coordinator import RecoveryCoordinator
from akaal.streaming.flow.backpressure import BackpressureController

logger = logging.getLogger(__name__)


class CDCTransactionOrderingCoordinator:
    """Master Master Orchestrator for CDC Transactional Ordering & Replay Safety."""

    def __init__(
        self,
        identity: CDCEventIdentity,
        parallel_engine: Optional[CDCParallelApplyEngine] = None,
        recovery_coordinator: Optional[RecoveryCoordinator] = None,
        state_store: Optional[CentralStateStore] = None,
        schema_barrier: Optional[CDCSchemaTransitionBarrier] = None,
        backpressure_controller: Optional[BackpressureController] = None,
        fk_relationships: Optional[Dict[str, str]] = None,
    ) -> None:
        self.identity = identity
        self.recovery_coordinator = recovery_coordinator or RecoveryCoordinator()
        self.state_store = state_store or CentralStateStore()
        self.schema_barrier = schema_barrier or CDCSchemaTransitionBarrier(state_store=self.state_store)
        self.backpressure_controller = backpressure_controller or BackpressureController()

        self.parallel_engine = parallel_engine or CDCParallelApplyEngine(
            identity=self.identity,
            recovery_coordinator=self.recovery_coordinator,
            state_store=self.state_store,
            schema_barrier=self.schema_barrier,
            backpressure_controller=self.backpressure_controller,
        )

        self.causality_graph = CDCCausalityGraphEngine(
            cdc_session_id=self.identity.cdc_session_id,
            state_store=self.state_store,
            fk_relationships=fk_relationships,
        )

        self.eligibility_engine = CDCReplayEligibilityEngine(
            causality_graph=self.causality_graph,
            schema_barrier=self.schema_barrier,
            cross_partition_barrier=self.parallel_engine.barrier_authority,
            recovery_coordinator=self.recovery_coordinator,
        )

        self._is_paused = False

    def register_and_evaluate_transaction(self, transaction: CDCTransaction, fencing_epoch: int) -> CDCOrderingDecision:
        """
        Registers transaction in causality graph, evaluates replay eligibility, and dispatches if READY.
        """
        if self._is_paused:
            return CDCOrderingDecision(
                tx_id=transaction.tx_id,
                eligibility=CDCReplayEligibility.BLOCKED_BY_DEPENDENCY,
                reason="Ordering coordinator is paused",
            )

        # 1. Identity isolation check
        if (
            transaction.identity.migration_id != self.identity.migration_id
            or transaction.identity.cdc_session_id != self.identity.cdc_session_id
        ):
            fail = CDCFailure(
                failure_type=CDCFailureType.DEPENDENCY_IDENTITY_MISMATCH,
                category=CDCFailureCategory.BLOCKING,
                message=f"[IDENTITY MISMATCH] Transaction '{transaction.tx_id}' identity does not match coordinator session '{self.identity.cdc_session_id}'.",
                migration_id=self.identity.migration_id,
                job_id=self.identity.job_id,
                run_id=self.identity.run_id,
                cdc_session_id=self.identity.cdc_session_id,
            )
            raise CDCExecutionError(fail)

        # 2. Add to causality graph (detects cycle and raises CAUSALITY_CYCLE_DETECTED if present)
        self.causality_graph.add_transaction(transaction)

        # 3. Evaluate eligibility
        decision = self.eligibility_engine.evaluate_eligibility(
            identity=self.identity,
            transaction=transaction,
            fencing_epoch=fencing_epoch,
            routing_generation=self.parallel_engine.routing_generation,
            active_engine_generation=self.parallel_engine.routing_generation,
        )

        # 4. Backpressure check based on graph size
        graph_summary = self.causality_graph.get_graph_summary()
        self.backpressure_controller.check_and_update(graph_summary["blocked_count"])

        # 5. Dispatch to P3.6 parallel engine if READY
        if decision.eligibility == CDCReplayEligibility.READY:
            self.parallel_engine.dispatch_transaction(transaction, fencing_epoch)

        return decision

    def record_transaction_completed(self, tx_id: str) -> List[str]:
        """Records completion of tx_id in causality graph, unblocking dependent successors."""
        unblocked = self.causality_graph.resolve_transaction_completion(tx_id)
        return unblocked

    def record_transaction_failed(self, tx_id: str) -> List[str]:
        """Records failure of tx_id in causality graph, blocking dependent successors."""
        affected = self.causality_graph.resolve_transaction_failure(tx_id)
        return affected

    def is_fully_drained(self) -> bool:
        """
        Evaluates whether ordering coordinator and parallel pipeline are fully drained.
        Blocks cutover if unresolved graph nodes, blocked transactions, or active barriers exist.
        """
        summary = self.causality_graph.get_graph_summary()
        if summary["blocked_count"] > 0:
            return False
        if not self.parallel_engine.is_fully_drained():
            return False
        return True

    def pause(self) -> None:
        self._is_paused = True
        self.parallel_engine.pause()

    def resume(self) -> None:
        self._is_paused = False
        self.parallel_engine.resume()

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns backend-authoritative ordering and causality telemetry DTO."""
        graph_sum = self.causality_graph.get_graph_summary()
        par_telem = self.parallel_engine.get_telemetry()
        return {
            "cdc_session_id": self.identity.cdc_session_id,
            "is_paused": self._is_paused,
            "causal_graph_summary": graph_sum,
            "parallel_engine_telemetry": par_telem,
        }
