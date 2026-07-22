"""
Checkpoint and Position Contracts for CDC Synchronization.
"""

from typing import Dict, Any, Optional
import datetime
from pydantic import BaseModel, Field


class Position(BaseModel):
    engine: str
    stream_position: str  # LSN / GTID / SCN / OpLog Timestamp
    tx_id: Optional[str] = None
    file_name: Optional[str] = None
    offset: int = 0


class Checkpoint(BaseModel):
    checkpoint_id: str
    stream_id: str
    source_db: str
    position: Position
    updated_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)
