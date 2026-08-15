"""
AKAAL CDC Engine Consistency Boundary Domain Models.
=====================================================
Formalizes the Initial Load -> CDC Consistency Boundary guaranteeing zero change loss
between initial snapshot capture and continuous CDC application.
"""

from enum import Enum
from typing import Dict, Any, Optional
import datetime

from akaal.cdc.domain.positions import CDCSourcePosition


class ConsistencyBoundaryState(str, Enum):
    """Lifecycle state of the Initial Load -> CDC consistency boundary."""
    UNINITIALIZED = "UNINITIALIZED"
    SNAPSHOT_CAPTURED = "SNAPSHOT_CAPTURED"
    BULK_TRANSPORT_ACTIVE = "BULK_TRANSPORT_ACTIVE"
    BULK_TRANSPORT_COMPLETE = "BULK_TRANSPORT_COMPLETE"
    CDC_BUFFERING_ACTIVE = "CDC_BUFFERING_ACTIVE"
    CDC_CATCHUP_ACTIVE = "CDC_CATCHUP_ACTIVE"
    CONSISTENT_SYNCHRONIZED = "CONSISTENT_SYNCHRONIZED"
    BOUNDARY_VIOLATED = "BOUNDARY_VIOLATED"


class CDCConsistencyBoundary:
    """
    Canonical Initial Load -> CDC Consistency Boundary.
    Enforces that CDC capture position <= initial load snapshot position, separating:
    - initial_load_snapshot_position
    - cdc_capture_start_position
    - last_durably_captured_position
    - last_durably_applied_position
    - last_acknowledged_position
    """

    def __init__(
        self,
        migration_id: str,
        job_id: str,
        run_id: str,
        initial_load_snapshot_position: CDCSourcePosition,
        cdc_capture_start_position: Optional[CDCSourcePosition] = None,
    ) -> None:
        self.migration_id = migration_id
        self.job_id = job_id
        self.run_id = run_id
        self.initial_load_snapshot_position = initial_load_snapshot_position
        # Default CDC capture start to initial load snapshot position to prevent gaps!
        self.cdc_capture_start_position = cdc_capture_start_position or initial_load_snapshot_position

        # Validate that capture start position is NOT after initial load snapshot position!
        if self.cdc_capture_start_position.is_after(self.initial_load_snapshot_position):
            raise ValueError(
                f"[CONSISTENCY BOUNDARY ERROR] CDC capture start position ({self.cdc_capture_start_position}) "
                f"is AFTER initial load snapshot position ({self.initial_load_snapshot_position})! "
                "Changes committed during initial bulk load would be lost."
            )

        self.last_durably_captured_position: Optional[CDCSourcePosition] = None
        self.last_durably_applied_position: Optional[CDCSourcePosition] = None
        self.last_acknowledged_position: Optional[CDCSourcePosition] = None

        self.boundary_state = ConsistencyBoundaryState.SNAPSHOT_CAPTURED
        self.created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.synchronized_at: Optional[str] = None

    def update_captured_position(self, pos: CDCSourcePosition) -> None:
        """Updates last durably captured position ensuring monotonicity."""
        if self.last_durably_captured_position and self.last_durably_captured_position.is_after(pos):
            raise ValueError(f"Non-monotonic capture position regression: {pos} < {self.last_durably_captured_position}")
        self.last_durably_captured_position = pos

    def update_applied_position(self, pos: CDCSourcePosition) -> None:
        """Updates last durably applied position ensuring it does not exceed captured position."""
        if self.last_durably_captured_position and pos.is_after(self.last_durably_captured_position):
            raise ValueError(f"Applied position {pos} cannot exceed captured position {self.last_durably_captured_position}")
        self.last_durably_applied_position = pos

    def update_acknowledged_position(self, pos: CDCSourcePosition) -> None:
        """Updates last acknowledged position ensuring it does not exceed applied position."""
        if self.last_durably_applied_position and pos.is_after(self.last_durably_applied_position):
            raise ValueError(f"Acknowledged position {pos} cannot exceed applied position {self.last_durably_applied_position}")
        self.last_acknowledged_position = pos

    def transition_state(self, target_state: ConsistencyBoundaryState) -> None:
        self.boundary_state = target_state
        if target_state == ConsistencyBoundaryState.CONSISTENT_SYNCHRONIZED:
            self.synchronized_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "migration_id": self.migration_id,
            "job_id": self.job_id,
            "run_id": self.run_id,
            "boundary_state": self.boundary_state.value,
            "initial_load_snapshot_position": self.initial_load_snapshot_position.to_dict(),
            "cdc_capture_start_position": self.cdc_capture_start_position.to_dict(),
            "last_durably_captured_position": self.last_durably_captured_position.to_dict() if self.last_durably_captured_position else None,
            "last_durably_applied_position": self.last_durably_applied_position.to_dict() if self.last_durably_applied_position else None,
            "last_acknowledged_position": self.last_acknowledged_position.to_dict() if self.last_acknowledged_position else None,
            "created_at": self.created_at,
            "synchronized_at": self.synchronized_at,
        }
