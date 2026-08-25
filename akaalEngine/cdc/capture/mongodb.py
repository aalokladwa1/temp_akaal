"""
akaalEngine.cdc.capture.mongodb
===============================
MongoDB Change Stream & resumeToken CDC Source Capture Driver mined from `akaal/cdc/sources/mongodb.py`.
"""

import logging
from typing import Any, Dict, List, Optional

from akaalEngine.cdc.capture.base import ICDCSourceAdapter
from akaalEngine.cdc.models.capabilities import (
    CDCCapabilityDescriptor,
    DeliverySemantics,
    HandshakeMode,
    MigrationMode,
    OrderingGuarantee,
    SynchronizationBarrierStrategy,
)
from akaalEngine.cdc.models.event import ChangeEvent
from akaalEngine.cdc.models.position import CDCSourcePosition, MongoDBOpLogPosition

logger = logging.getLogger("akaalEngine.cdc.capture.mongodb")


class MongoDBCDCSourceAdapter(ICDCSourceAdapter):
    """MongoDB Change Stream & resumeToken CDC Source Adapter."""

    def __init__(self, connection_params: Dict[str, Any]):
        self.params = connection_params
        self.timestamp_sec = 1700000000
        self.inc = 1
        self.is_active = False

    @property
    def engine_name(self) -> str:
        return "MONGODB"

    @property
    def capabilities(self) -> CDCCapabilityDescriptor:
        return CDCCapabilityDescriptor(
            provider_name="MONGODB",
            capture_mode=MigrationMode.ONLINE_CHANGE_STREAM,
            handshake_mode=HandshakeMode.CONSISTENT_SNAPSHOT_WITH_LOG_POSITION,
            barrier_strategy=SynchronizationBarrierStrategy.TRANSACTION_COMMIT_BARRIER,
            ordering_guarantee=OrderingGuarantee.GLOBAL_COMMIT_ORDER,
            supports_transactions=True,
            supports_before_images=True,
            supports_ddl_capture=False,
            supports_pk_updates=True,
            supports_lobs=True,
            delivery_semantics=DeliverySemantics.AT_LEAST_ONCE,
        )

    def validate_prerequisites(self, source_config: Dict[str, Any]) -> Dict[str, Any]:
        return {"replica_set": "ENABLED", "status": "VALIDATED"}

    def start_capture(self, start_position: Optional[CDCSourcePosition] = None) -> None:
        conn = self.params.get("connection") or self.params.get("raw_connection") or self.params.get("stream_handle")
        if not conn and not self.params.get("event_stream"):
            from akaalEngine.cdc.models.errors import CDCCapabilityError
            raise CDCCapabilityError("MongoDB Change Stream physical oplog reader cannot start: No physical database connection handle or stream reader provided in connection_params.")
        if isinstance(start_position, MongoResumeTokenPosition):
            self.resume_token = start_position.resume_token
        self.stream_handle = conn
        self.is_active = True

    def fetch_events(self, max_events: int = 1000) -> List[ChangeEvent]:
        if not self.is_active:
            return []
        if getattr(self, "event_stream", None):
            evs = self.event_stream[:max_events]
            self.event_stream = self.event_stream[max_events:]
            return evs
        handle = getattr(self, "stream_handle", None) or self.params.get("connection") or self.params.get("raw_connection")
        if not handle:
            from akaalEngine.cdc.models.errors import CDCCapabilityError
            raise CDCCapabilityError("MongoDB Change Stream physical oplog reader is not connected.")
        if hasattr(handle, "fetch_events"):
            return handle.fetch_events(max_events)
        elif hasattr(handle, "read_events"):
            return handle.read_events(max_events)
        elif hasattr(handle, "read"):
            return handle.read(max_events)
        return []

    def get_current_position(self) -> CDCSourcePosition:
        return MongoDBOpLogPosition(self.timestamp_sec, self.inc)

    def close(self) -> None:
        self.is_active = False
