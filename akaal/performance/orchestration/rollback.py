"""
Optimization Rollback Controller.
Reverts performance tuning changes if degradation is validated.
"""

from typing import Dict, Any, Callable, Optional
import logging

from akaal.performance.orchestration.optimization_session import OptimizationSession, OptimizationState
from akaal.performance.orchestration.snapshot import OptimizationSnapshotManager

logger = logging.getLogger("nexusforge.performance.orchestration.rollback")


class OptimizationRollbackController:
    """Orchestrates configuration restoration upon performance failures or degradation."""

    def __init__(self, snapshot_manager: OptimizationSnapshotManager, apply_config_cb: Callable[[Dict[str, Any]], None]) -> None:
        self.snapshot_manager = snapshot_manager
        self.apply_config_cb = apply_config_cb

    def execute_rollback(self, session: OptimizationSession, reason: str) -> None:
        """Restores the configuration back to pre-optimization snapshot variables."""
        pre_snap = self.snapshot_manager.get_snapshot(session.session_id, "Pre-Optimization")
        if not pre_snap:
            logger.error(f"Cannot perform rollback for session {session.session_id}: Pre-Optimization snapshot not found.")
            session.transition_to(OptimizationState.FAILED, "Rollback failed: No pre-optimization snapshot.")
            return

        try:
            logger.warning(f"Triggering rollback for session {session.session_id}. Reason: {reason}")
            
            # Apply previous config
            self.apply_config_cb(pre_snap.runtime_config)

            # Record event
            session.rollback_events.append({
                "timestamp": session.end_time or "",
                "reason": reason,
                "restored_config": pre_snap.runtime_config
            })

            # Capture Rollback snapshot
            self.snapshot_manager.capture_snapshot(
                session_id=session.session_id,
                snapshot_type="Rollback",
                runtime_config=pre_snap.runtime_config,
                active_profile=pre_snap.active_profile,
                active_rules=pre_snap.active_rules,
                active_policies=pre_snap.active_policies,
                resource_limits=pre_snap.resource_limits,
                metrics=pre_snap.metrics,
                health_score=pre_snap.health_score,
                optimizer_states=pre_snap.optimizer_states
            )

            session.transition_to(OptimizationState.ROLLED_BACK, reason)

        except Exception as e:
            logger.error(f"Failed to execute rollback for session {session.session_id}: {str(e)}", exc_info=True)
            session.transition_to(OptimizationState.FAILED, f"Rollback failed during configuration restoration: {str(e)}")
