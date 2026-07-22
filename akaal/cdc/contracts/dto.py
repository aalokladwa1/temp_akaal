"""
DTO Contracts for CDC Operations.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CDCSessionDTO(BaseModel):
    session_id: str
    source_engine: str
    source_db: str
    target_dbs: List[str] = Field(default_factory=list)
    status: str = "RUNNING"  # RUNNING, PAUSED, STOPPED, FAILED
    captured_events_count: int = 0
    start_time: str
    last_position: Optional[str] = None


class CDCRouteDTO(BaseModel):
    route_id: str
    source_table_pattern: str
    target_destination: str
    filter_condition: Optional[str] = None
    is_active: bool = True


class ReplayResultDTO(BaseModel):
    replay_id: str
    start_position: str
    end_position: str
    replayed_events_count: int
    duration_ms: float
    status: str = "COMPLETED"


class FailoverStatusDTO(BaseModel):
    failover_id: str
    node_id: str
    status: str = "COMPLETED"
    recovered_session_count: int = 1
    timestamp: str
