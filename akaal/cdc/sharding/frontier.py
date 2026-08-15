"""
AKAAL Contiguous Checkpoint Frontier Tracker (P3.6).
====================================================
Tracks transaction completions out-of-order across parallel workers.
Computes the contiguous source position frontier so that global checkpoints never skip uncompleted earlier transactions.
"""

import logging
from typing import Dict, Any, List, Optional
from akaal.cdc.domain.positions import CDCSourcePosition

logger = logging.getLogger(__name__)


class CDCCheckpointFrontierTracker:
    """Tracks out-of-order parallel completions to compute monotonic contiguous checkpoint frontier."""

    def __init__(self, initial_position: Optional[CDCSourcePosition] = None) -> None:
        self.initial_position = initial_position
        self.completed_positions: List[CDCSourcePosition] = []
        self.pending_positions: List[CDCSourcePosition] = []
        self._frontier_position: Optional[CDCSourcePosition] = initial_position

    def register_pending_transaction(self, commit_position: CDCSourcePosition) -> None:
        """Registers a transaction position when dispatched to a worker queue."""
        if commit_position not in self.pending_positions:
            self.pending_positions.append(commit_position)
            # Maintain sorted order of positions
            self.pending_positions.sort()

    def record_completed_transaction(self, commit_position: CDCSourcePosition) -> CDCSourcePosition:
        """
        Records completion of a transaction position.
        Updates and returns the contiguous completed frontier position.
        """
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
        return self._frontier_position

    @property
    def frontier_position(self) -> Optional[CDCSourcePosition]:
        return self._frontier_position

    def is_position_checkpoint_eligible(self, position: CDCSourcePosition) -> bool:
        """Returns True if position is <= the current contiguous frontier."""
        if self._frontier_position is None:
            return False
        return position <= self._frontier_position
