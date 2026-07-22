"""
Abstract CDC Target Adapter Interface.
"""

from abc import ABC, abstractmethod
from typing import List
from akaal.cdc.contracts.event import CDCEvent


class ICDCTargetAdapter(ABC):
    """Abstract Interface for CDC Target Database Adapters."""

    @abstractmethod
    async def apply_changes(self, events: List[CDCEvent]) -> bool:
        """Idempotently apply CDC change events to target database."""
        pass
