"""
Enterprise Domain Event Definitions.
"""

from typing import Any, Dict, Optional
import datetime
import uuid
from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:12]}")
    event_type: str
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    tenant_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class MigrationStarted(DomainEvent):
    event_type: str = "MigrationStarted"


class MigrationCompleted(DomainEvent):
    event_type: str = "MigrationCompleted"


class MigrationFailed(DomainEvent):
    event_type: str = "MigrationFailed"


class SchemaChanged(DomainEvent):
    event_type: str = "SchemaChanged"


class ValidationFinished(DomainEvent):
    event_type: str = "ValidationFinished"


class JobCancelled(DomainEvent):
    event_type: str = "JobCancelled"
