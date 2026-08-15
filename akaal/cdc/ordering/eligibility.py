"""
AKAAL CDC Replay Eligibility Engine (P3.7).
============================================
Backend-authoritative evaluation of transaction replay eligibility.
Combines causality graph dependencies, P3.5 schema barriers, P3.6 cross-partition barriers,
worker fencing tokens, and predecessor resolution states.
"""

import logging
from typing import Dict, Any, List, Optional
from akaal.cdc.domain.events import CDCEventIdentity, CDCTransaction
from akaal.cdc.ordering.domain import (
    CDCReplayEligibility,
    CDCOrderingDecision,
)
from akaal.cdc.ordering.causality import CDCCausalityGraphEngine
from akaal.cdc.schema_evolution.barrier import CDCSchemaTransitionBarrier
from akaal.cdc.sharding.barrier import CDCCrossPartitionOrderingBarrier
from akaal.runtime.recovery.coordinator import RecoveryCoordinator

logger = logging.getLogger(__name__)


class CDCReplayEligibilityEngine:
    """Canonical Backend-Authoritative Replay Eligibility Engine."""

    def __init__(
        self,
        causality_graph: CDCCausalityGraphEngine,
        schema_barrier: Optional[CDCSchemaTransitionBarrier] = None,
        cross_partition_barrier: Optional[CDCCrossPartitionOrderingBarrier] = None,
        recovery_coordinator: Optional[RecoveryCoordinator] = None,
    ) -> None:
        self.causality_graph = causality_graph
        self.schema_barrier = schema_barrier
        self.cross_partition_barrier = cross_partition_barrier
        self.recovery_coordinator = recovery_coordinator or RecoveryCoordinator()

    def evaluate_eligibility(
        self,
        identity: CDCEventIdentity,
        transaction: CDCTransaction,
        fencing_epoch: int,
        partition_id: int = 0,
        routing_generation: int = 1,
        active_engine_generation: int = 1,
    ) -> CDCOrderingDecision:
        """
        Evaluates full backend-authoritative replay eligibility for a transaction.
        Checks identity, generation, fencing, causality, schema barrier, and cross-partition barrier.
        """
        tx_id = transaction.tx_id

        # 1. Identity isolation check
        if (
            identity.migration_id != transaction.identity.migration_id
            or identity.cdc_session_id != transaction.identity.cdc_session_id
        ):
            return CDCOrderingDecision(
                tx_id=tx_id,
                eligibility=CDCReplayEligibility.REJECTED_IDENTITY_MISMATCH,
                reason=f"Identity mismatch: expected session '{identity.cdc_session_id}', got '{transaction.identity.cdc_session_id}'",
            )

        # 2. Routing generation check
        if routing_generation != active_engine_generation:
            return CDCOrderingDecision(
                tx_id=tx_id,
                eligibility=CDCReplayEligibility.REJECTED_STALE_GENERATION,
                reason=f"Stale routing generation: tx gen {routing_generation} != active gen {active_engine_generation}",
            )

        # 3. Fencing token validation
        if not self.recovery_coordinator.validate_fencing_token(identity.migration_id, fencing_epoch):
            return CDCOrderingDecision(
                tx_id=tx_id,
                eligibility=CDCReplayEligibility.BLOCKED_BY_FENCING,
                reason=f"Fencing token epoch {fencing_epoch} rejected as stale by RecoveryCoordinator",
            )

        # 4. Failed predecessor check
        if self.causality_graph.has_failed_predecessor(tx_id):
            blockers = self.causality_graph.get_blocker_tx_ids(tx_id)
            return CDCOrderingDecision(
                tx_id=tx_id,
                eligibility=CDCReplayEligibility.BLOCKED_BY_FAILED_PREDECESSOR,
                reason=f"Predecessor transaction in dependency chain failed",
                blocker_tx_ids=blockers,
            )

        # 5. Causality graph dependencies check
        blockers = self.causality_graph.get_blocker_tx_ids(tx_id)
        if blockers:
            return CDCOrderingDecision(
                tx_id=tx_id,
                eligibility=CDCReplayEligibility.BLOCKED_BY_DEPENDENCY,
                reason=f"Blocked by {len(blockers)} unresolved predecessor transactions: {blockers}",
                blocker_tx_ids=blockers,
            )

        # 6. P3.5 Schema Barrier check
        if self.schema_barrier:
            for evt in transaction.events:
                if self.schema_barrier.is_barrier_active(identity.cdc_session_id, evt.source_table):
                    return CDCOrderingDecision(
                        tx_id=tx_id,
                        eligibility=CDCReplayEligibility.BLOCKED_BY_SCHEMA,
                        reason=f"Active schema transition barrier set for table '{evt.source_table}'",
                    )

        # 7. P3.6 Cross-Partition Barrier check
        if self.cross_partition_barrier:
            if self.cross_partition_barrier.is_partition_locked(identity.cdc_session_id, partition_id, tx_id):
                return CDCOrderingDecision(
                    tx_id=tx_id,
                    eligibility=CDCReplayEligibility.BLOCKED_BY_CROSS_PARTITION_BARRIER,
                    reason=f"Partition {partition_id} locked by another multi-partition transaction",
                )

        # All checks passed: READY
        return CDCOrderingDecision(
            tx_id=tx_id,
            eligibility=CDCReplayEligibility.READY,
            reason="All causality, schema, fencing, and ordering constraints satisfied.",
        )
