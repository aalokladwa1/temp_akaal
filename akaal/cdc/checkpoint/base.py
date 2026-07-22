"""
Abstract Checkpoint Store Interface.
"""

from abc import ABC, abstractmethod
from typing import Optional
from akaal.cdc.contracts.checkpoint import Checkpoint


class ICheckpointStore(ABC):
    """Abstract Interface for CDC Checkpoint Persistence Stores."""

    @abstractmethod
    async def save_checkpoint(self, checkpoint: Checkpoint) -> bool:
        """Persist stream position checkpoint."""
        pass

    @abstractmethod
    async def load_checkpoint(self, stream_id: str) -> Optional[Checkpoint]:
        """Load latest stream position checkpoint."""
        pass
