"""
ClusterStateMachine module.
Enforces legal ClusterState transitions explicitly.
"""

from typing import Dict, Set
import logging

from akaal.distributed.domain.enums import ClusterState
from akaal.distributed.domain.errors import ClusterStateError

logger = logging.getLogger("nexusforge.distributed.cluster_state")


class ClusterStateMachine:
    """
    Enforces valid state transitions for ClusterState.
    """

    ALLOWED_TRANSITIONS: Dict[ClusterState, Set[ClusterState]] = {
        ClusterState.INITIALIZING: {ClusterState.FORMING, ClusterState.FAILED},
        ClusterState.FORMING: {ClusterState.HEALTHY, ClusterState.DEGRADED, ClusterState.FAILED},
        ClusterState.HEALTHY: {ClusterState.DEGRADED, ClusterState.FAILED},
        ClusterState.DEGRADED: {ClusterState.HEALTHY, ClusterState.RECOVERING, ClusterState.FAILED},
        ClusterState.RECOVERING: {ClusterState.HEALTHY, ClusterState.DEGRADED, ClusterState.FAILED},
        ClusterState.FAILED: {ClusterState.RECOVERING, ClusterState.INITIALIZING},
    }

    def validate_transition(self, current: ClusterState, target: ClusterState) -> None:
        if current == target:
            return
        allowed = self.ALLOWED_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ClusterStateError(f"Illegal cluster state transition: {current.value} -> {target.value}")

    def transition(self, current: ClusterState, target: ClusterState) -> ClusterState:
        self.validate_transition(current, target)
        return target
