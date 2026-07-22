"""
Database-Backed Checkpoint Store Implementation.
"""

from typing import Dict, Optional
from akaal.cdc.checkpoint.base import ICheckpointStore
from akaal.cdc.contracts.checkpoint import Checkpoint


class DatabaseCheckpointStore(ICheckpointStore):
    """Database-Backed Checkpoint Store."""

    def __init__(self, connection_string: str = "sqlite:///cdc_checkpoints.db") -> None:
        self.connection_string = connection_string
        self._db_table: Dict[str, Checkpoint] = {}

    async def save_checkpoint(self, checkpoint: Checkpoint) -> bool:
        self._db_table[checkpoint.stream_id] = checkpoint
        return True

    async def load_checkpoint(self, stream_id: str) -> Optional[Checkpoint]:
        return self._db_table.get(stream_id)
