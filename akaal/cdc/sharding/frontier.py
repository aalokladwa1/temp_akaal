"""
AKAAL Contiguous Checkpoint Frontier Tracker (P3.6).
====================================================
Tracks transaction completions out-of-order across parallel workers.
Computes the contiguous source position frontier so that global checkpoints never skip uncompleted earlier transactions.
"""

import threading
import logging
from typing import Dict, Any, List, Optional
from akaal.cdc.domain.positions import CDCSourcePosition, parse_source_position
from akaal.core.state.state_store import CentralStateStore

logger = logging.getLogger(__name__)


class CDCCheckpointFrontierTracker:
    """Tracks out-of-order parallel completions to compute monotonic contiguous checkpoint frontier."""

    def __init__(
        self,
        initial_position: Optional[CDCSourcePosition] = None,
        state_store: Optional[CentralStateStore] = None,
        cdc_session_id: Optional[str] = None,
    ) -> None:
        self._lock = threading.RLock()
        self.initial_position = initial_position
        self.completed_positions: List[CDCSourcePosition] = []
        self.pending_positions: List[CDCSourcePosition] = []
        self._frontier_position: Optional[CDCSourcePosition] = initial_position
        self.state_store = state_store
        self.cdc_session_id = cdc_session_id

        if self.state_store and self.cdc_session_id:
            self.reconstruct_from_state_store()

    def _persist_state(self) -> None:
        if self.state_store and self.cdc_session_id:
            state_key = f"cdc_frontier_{self.cdc_session_id}"
            payload = {
                "frontier_position": self._frontier_position.to_dict() if self._frontier_position else None,
                "pending_positions": [p.to_dict() for p in self.pending_positions],
                "completed_positions": [p.to_dict() for p in self.completed_positions],
            }
            self.state_store.set_state(state_key, payload, category="checkpoint_frontier")

    def reconstruct_from_state_store(self) -> bool:
        if not self.state_store or not self.cdc_session_id:
            return False
        with self._lock:
            state_key = f"cdc_frontier_{self.cdc_session_id}"
            data = self.state_store.get_state(state_key, category="checkpoint_frontier")
            if data and isinstance(data, dict):
                if data.get("frontier_position"):
                    self._frontier_position = parse_source_position(data["frontier_position"])
                self.pending_positions = [parse_source_position(p) for p in data.get("pending_positions", [])]
                self.completed_positions = [parse_source_position(p) for p in data.get("completed_positions", [])]
                logger.info(f"[FrontierTracker] Reconstructed frontier position '{self._frontier_position}' for session '{self.cdc_session_id}'")
                return True
            return False

    def register_pending_transaction(self, commit_position: CDCSourcePosition) -> None:
        """Registers a transaction position when dispatched to a worker queue."""
        with self._lock:
            if commit_position not in self.pending_positions:
                self.pending_positions.append(commit_position)
                self.pending_positions.sort()
                self._persist_state()

    def record_completed_transaction(self, commit_position: CDCSourcePosition) -> CDCSourcePosition:
        """
        Records completion of a transaction position.
        Updates and returns the contiguous completed frontier position.
        """
        with self._lock:
            if commit_position in self.pending_positions:
                self.pending_positions.remove(commit_position)

            if commit_position not in self.completed_positions:
                self.completed_positions.append(commit_position)
                self.completed_positions.sort()

            # Compute new contiguous frontier
            # The frontier is the highest position such that all positions <= frontier are completed.
            new_frontier = self._frontier_position

            for pos in self.completed_positions:
                # Check if there are any pending positions less than pos
                has_uncompleted_earlier = any(p < pos for p in self.pending_positions)
                if not has_uncompleted_earlier:
                    if new_frontier is None or pos > new_frontier:
                        new_frontier = pos
                else:
                    # Cannot advance past this uncompleted earlier position
                    break

            self._frontier_position = new_frontier
            self._persist_state()
            return self._frontier_position

    @property
    def frontier_position(self) -> Optional[CDCSourcePosition]:
        with self._lock:
            return self._frontier_position

    def is_position_checkpoint_eligible(self, position: CDCSourcePosition) -> bool:
        """Returns True if position is <= the current contiguous frontier."""
        with self._lock:
            if self._frontier_position is None:
                return False
            return position <= self._frontier_position
