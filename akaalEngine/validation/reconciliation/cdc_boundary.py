"""
akaalEngine.validation.reconciliation.cdc_boundary
===================================================
CDCBoundaryReconciler for Authority #11 (VAL-033, VAL-034).
Anchors final reconciliation to Authority #10 synchronized CDC boundary and rejects unresolved CDC state.
"""

import logging
from typing import Any, Dict, Optional, Tuple, List

from akaalEngine.validation.models.errors import ValidationError

logger = logging.getLogger("akaalEngine.validation.reconciliation.cdc_boundary")


class CDCBoundaryReconciler:
    """
    Validates that final reconciliation is anchored to a synchronized Authority #10 CDC boundary.
    Fails closed if CDC has open transactions, ambiguous commits, or undrained backlog.
    """

    def validate_cdc_boundary(
        self,
        cdc_snapshot: Optional[Dict[str, Any]] = None,
        target_applied_position: Optional[str] = None,
        required_boundary_position: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Validates Authority #10 CDC state for final validation gate.
        Returns (boundary_valid, list_of_rejection_reasons).
        """
        reasons: List[str] = []
        if not cdc_snapshot:
            # Non-CDC migration or snapshot-only
            return True, []

        open_txs = cdc_snapshot.get("open_transactions", 0)
        ambiguous_commits = cdc_snapshot.get("ambiguous_commit_count", 0)
        barrier_reached = cdc_snapshot.get("synchronization_barrier_reached", True)
        backlog_events = cdc_snapshot.get("backlog_events", 0)

        # VAL-034: Fail closed on unresolved CDC state
        if open_txs > 0:
            reasons.append(f"CDC has {open_txs} open/unresolved transactions!")
        if ambiguous_commits > 0:
            reasons.append(f"CDC has {ambiguous_commits} ambiguous commits!")
        if not barrier_reached:
            reasons.append("CDC synchronization barrier not reached!")
        if backlog_events > 0:
            reasons.append(f"CDC backlog has {backlog_events} undrained events!")

        if required_boundary_position and target_applied_position:
            if target_applied_position < required_boundary_position:
                reasons.append(f"Target applied position '{target_applied_position}' is behind required CDC boundary '{required_boundary_position}'!")

        valid = len(reasons) == 0
        if not valid:
            logger.warning(f"CDC Boundary Validation REJECTED: {reasons}")

        return valid, reasons
