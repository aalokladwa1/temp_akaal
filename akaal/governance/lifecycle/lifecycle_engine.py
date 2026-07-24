"""
AKAAL Platform 6 — Governance Lifecycle Management Engine.
"""

from typing import Dict, List, Optional
import datetime
import uuid

from akaal.governance.domain.enums import LifecycleState
from akaal.governance.domain.models import LifecycleTransition
from akaal.governance.domain.exceptions import LifecycleValidationError
from akaal.governance.lifecycle.transitions import LifecycleTransitionValidator


class GovernanceLifecycleEngine:
    """Enforces state transitions and audit logging across all governance artifact lifecycles."""

    def __init__(self) -> None:
        self._validator = LifecycleTransitionValidator()
        self._current_states: Dict[str, LifecycleState] = {}
        self._history: Dict[str, List[LifecycleTransition]] = {}

    def initialize_artifact(self, artifact_id: str, initial_state: LifecycleState = LifecycleState.DRAFT) -> None:
        self._current_states[artifact_id] = initial_state
        self._history[artifact_id] = []

    def get_state(self, artifact_id: str) -> LifecycleState:
        return self._current_states.get(artifact_id, LifecycleState.DRAFT)

    def transition_state(self, artifact_id: str, target_state: LifecycleState, actor_id: str, justification: str = "") -> LifecycleTransition:
        curr_state = self.get_state(artifact_id)
        valid, msg = self._validator.validate_transition(curr_state, target_state)
        if not valid:
            raise LifecycleValidationError(msg)

        transition_id = f"trn-{uuid.uuid4().hex[:8]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        record = LifecycleTransition(
            transition_id=transition_id,
            artifact_id=artifact_id,
            from_state=curr_state,
            to_state=target_state,
            actor_id=actor_id,
            timestamp=now,
            justification=justification,
        )

        self._current_states[artifact_id] = target_state
        if artifact_id not in self._history:
            self._history[artifact_id] = []
        self._history[artifact_id].append(record)

        return record

    def get_transition_history(self, artifact_id: str) -> List[LifecycleTransition]:
        return self._history.get(artifact_id, [])
