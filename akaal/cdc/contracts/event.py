"""
CDC Event & Transaction Data Models.
"""

from typing import Any, Dict, Optional
import datetime
import uuid
from enum import Enum
try:
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)
        def dict(self):
            return self.__dict__
        def model_dump(self):
            return self.__dict__
    def Field(default=None, default_factory=None, **kwargs):
        return default


class ChangeType(str, Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    DDL = "DDL"


class TransactionContext(BaseModel):
    tx_id: str
    commit_timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    sequence_number: int = 1
    total_events_in_tx: int = 1


class CDCEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"cdc-{uuid.uuid4().hex[:12]}")
    source_engine: str  # POSTGRES, MYSQL, ORACLE, SQLSERVER, MONGODB, TRIGGER
    source_db: str
    source_schema: str
    source_table: str
    change_type: ChangeType
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    tx_context: Optional[TransactionContext] = None
    tenant_id: Optional[str] = None
    position_lsn: Optional[str] = None  # LSN / GTID / SCN / OpLog position
