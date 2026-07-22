"""
File-Based Checkpoint Store Implementation.
"""

from typing import Optional
import json
import os
from akaal.cdc.checkpoint.base import ICheckpointStore
from akaal.cdc.contracts.checkpoint import Checkpoint, Position


class FileCheckpointStore(ICheckpointStore):
    """File-Based Persistent Checkpoint Store."""

    def __init__(self, directory: str = ".cdc_checkpoints") -> None:
        self.directory = directory

    def _get_path(self, stream_id: str) -> str:
        safe_id = stream_id.replace("/", "_").replace(":", "_")
        return os.path.join(self.directory, f"{safe_id}.json")

    async def save_checkpoint(self, checkpoint: Checkpoint) -> bool:
        os.makedirs(self.directory, exist_ok=True)
        path = self._get_path(checkpoint.stream_id)
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(checkpoint.model_dump()))
        return True

    async def load_checkpoint(self, stream_id: str) -> Optional[Checkpoint]:
        path = self._get_path(stream_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.loads(f.read())
            return Checkpoint(**data)
