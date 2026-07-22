"""
In-Memory Checkpoint Store Implementation.
"""

from typing import Dict, Optional
from akaal.cdc.checkpoint.base import ICheckpointStore
from akaal.cdc.contracts.checkpoint import Checkpoint


class MemoryCheckpointStore(ICheckpointStore):
    """In-Memory Checkpoint Store."""

    def __init__(self) -> None:
        self._store: Dict[str, Checkpoint] = {}

    async def save_checkpoint(self, checkpoint: Checkpoint) -> bool:
        self._store[checkpoint.stream_id] = checkpoint
        return True

    async def load_checkpoint(self, stream_id: str) -> Optional[Checkpoint]:
        return self._store.get(stream_id)
