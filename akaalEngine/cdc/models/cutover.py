"""
akaalEngine.cdc.models.cutover
==============================
Cutover State Machine FSM enums and Technical Cutover Readiness facts DTO.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional


class CutoverState(str, Enum):
    SNAPSHOT_PREPARING = "SNAPSHOT_PREPARING"
    CAPTURE_STARTING = "CAPTURE_STARTING"
    SNAPSHOT_RUNNING = "SNAPSHOT_RUNNING"
    CDC_APPLYING = "CDC_APPLYING"
    CATCHING_UP = "CATCHING_UP"
    PRE_CUTOVER = "PRE_CUTOVER"
    SOURCE_QUIESCING = "SOURCE_QUIESCING"
    SOURCE_QUIESCED = "SOURCE_QUIESCED"
    FINAL_APPLY = "FINAL_APPLY"
    SYNC_BARRIER_WAIT = "SYNC_BARRIER_WAIT"
    SYNC_BARRIER_REACHED = "SYNC_BARRIER_REACHED"
    TECHNICAL_CUTOVER_READY = "TECHNICAL_CUTOVER_READY"
    CUTOVER_COMPLETE = "CUTOVER_COMPLETE"
    CUTOVER_FAILED = "CUTOVER_FAILED"


class ConvergenceState(str, Enum):
    CONVERGING = "CONVERGING"
    STABLE = "STABLE"
    DIVERGING = "DIVERGING"
    UNKNOWN = "UNKNOWN"


@dataclass
class TechnicalCutoverReadinessFacts:
    """Fact-based readiness gate for technical cutover execution."""
    snapshot_complete: bool
    replication_lag_seconds: float
    cdc_backlog_events: int
    unresolved_transactions: int
    ambiguous_commit_count: int
    checkpoint_identity_valid: bool
    source_position_barrier_reached: bool
    target_applied_barrier_reached: bool
    schema_transition_pending: bool = False

    @property
    def is_technical_cutover_ready(self) -> bool:
        """Evaluates whether all technical readiness facts permit cutover execution."""
        return (
            self.snapshot_complete
            and self.replication_lag_seconds <= 2.0
            and self.cdc_backlog_events == 0
            and self.unresolved_transactions == 0
            and self.ambiguous_commit_count == 0
            and self.checkpoint_identity_valid
            and self.source_position_barrier_reached
            and self.target_applied_barrier_reached
            and not self.schema_transition_pending
        )
