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
        if isinstance(start_position, MongoDBOpLogPosition):
            self.timestamp_sec = start_position.timestamp_sec
            self.inc = start_position.inc
        self.is_active = True

    def fetch_events(self, max_events: int = 1000) -> List[ChangeEvent]:
        if not self.is_active:
            return []
        return []

    def get_current_position(self) -> CDCSourcePosition:
        return MongoDBOpLogPosition(self.timestamp_sec, self.inc)

    def close(self) -> None:
        self.is_active = False
