"""
akaalEngine.cdc.models.transaction
==================================
CDCTransaction container grouping events for atomic commit reconstruction.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from akaalEngine.cdc.models.event import ChangeEvent, TransactionContext


@dataclass
class CDCTransaction:
    """Group of ChangeEvents belonging to the same atomic transaction."""
    tx_context: TransactionContext
    events: List[ChangeEvent] = field(default_factory=list)
    is_committed: bool = False
    is_rolled_back: bool = False

    def add_event(self, event: ChangeEvent) -> None:
        self.events.append(event)

    def mark_committed(self) -> None:
        self.is_committed = True

    def mark_rolled_back(self) -> None:
        self.is_rolled_back = True
