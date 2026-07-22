"""
Redis-Backed Checkpoint Store Implementation.
"""

from typing import Dict, Optional
from akaal.cdc.checkpoint.base import ICheckpointStore
from akaal.cdc.contracts.checkpoint import Checkpoint


class RedisCheckpointStore(ICheckpointStore):
    """Redis-Backed Checkpoint Store."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0") -> None:
        self.redis_url = redis_url
        self._redis_mock: Dict[str, Checkpoint] = {}

    async def save_checkpoint(self, checkpoint: Checkpoint) -> bool:
        self._redis_mock[f"chk:{checkpoint.stream_id}"] = checkpoint
        return True

    async def load_checkpoint(self, stream_id: str) -> Optional[Checkpoint]:
        return self._redis_mock.get(f"chk:{stream_id}")
