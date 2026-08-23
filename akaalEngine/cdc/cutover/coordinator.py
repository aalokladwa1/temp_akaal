"""
akaalEngine.cdc.cutover.coordinator
===================================
CutoverCoordinator managing legal FSM state transitions and readiness fact collection.
"""

import logging
from typing import Any, Dict, Optional

from akaalEngine.cdc.models.cutover import CutoverState, TechnicalCutoverReadinessFacts
from akaalEngine.cdc.models.errors import CDCCutoverNotReadyError

logger = logging.getLogger("akaalEngine.cdc.cutover.coordinator")


class CutoverCoordinator:
    """Manages Cutover FSM state machine lifecycle."""

    def __init__(self) -> None:
        self.state = CutoverState.SNAPSHOT_PREPARING

    def transition_to(self, new_state: CutoverState) -> None:
        """Executes legal FSM transition."""
        logger.info(f"[CutoverCoordinator] Transitioning from '{self.state.value}' to '{new_state.value}'")
        self.state = new_state

    def declare_technical_cutover_ready(self, facts: TechnicalCutoverReadinessFacts) -> None:
        """Evaluates readiness facts and transitions to TECHNICAL_CUTOVER_READY."""
        if not facts.is_technical_cutover_ready:
            raise CDCCutoverNotReadyError("Cannot declare TECHNICAL_CUTOVER_READY: readiness facts failed!")
        self.transition_to(CutoverState.TECHNICAL_CUTOVER_READY)
