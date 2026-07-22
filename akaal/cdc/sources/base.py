"""
Abstract CDC Source Adapter Interface.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Optional
from akaal.cdc.contracts.event import CDCEvent
from akaal.cdc.contracts.checkpoint import Position


class ICDCSourceAdapter(ABC):
    """Abstract Interface for all Database CDC Source Adapters."""

    @property
    @abstractmethod
    def engine_name(self) -> str:
        pass

    @abstractmethod
    async def start_capture(self, from_position: Optional[Position] = None) -> AsyncGenerator[CDCEvent, None]:
        """Stream CDC events from log position."""
        pass

    @abstractmethod
    async def get_current_position(self) -> Position:
        """Fetch current database WAL/Binlog/LogMiner position."""
        pass

    @abstractmethod
    async def stop_capture(self) -> None:
        """Stop change data capture stream."""
        pass
