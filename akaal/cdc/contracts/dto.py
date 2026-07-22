"""
DTO Contracts for CDC Operations.
"""

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
