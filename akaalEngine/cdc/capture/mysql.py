"""
akaalEngine.cdc.capture.mysql
=============================
MySQL & MariaDB Binlog ROW / GTID CDC Source Capture Driver mined from `akaal/cdc/sources/mysql.py`.
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
from akaalEngine.cdc.models.errors import CDCPermissionError
from akaalEngine.cdc.models.event import ChangeEvent
from akaalEngine.cdc.models.position import CDCSourcePosition, MariaDBGTIDPosition, MySQLGTIDPosition

logger = logging.getLogger("akaalEngine.cdc.capture.mysql")


class MySQLCDCSourceAdapter(ICDCSourceAdapter):
    """MySQL & MariaDB Binlog ROW format & GTID set inclusion CDC Source Adapter."""

    def __init__(self, connection_params: Dict[str, Any]):
        self.params = connection_params
        self.binlog_file = "mysql-bin.000001"
        self.binlog_pos = 120
        self.is_active = False

    @property
    def engine_name(self) -> str:
        return "MYSQL"

    @property
    def capabilities(self) -> CDCCapabilityDescriptor:
        return CDCCapabilityDescriptor(
            provider_name="MYSQL",
            capture_mode=MigrationMode.ONLINE_NATIVE_CDC,
            handshake_mode=HandshakeMode.CONSISTENT_SNAPSHOT_WITH_LOG_POSITION,
            barrier_strategy=SynchronizationBarrierStrategy.LOG_MARKER_INJECTION,
            ordering_guarantee=OrderingGuarantee.GLOBAL_COMMIT_ORDER,
            supports_transactions=True,
            supports_before_images=True,
            supports_ddl_capture=True,
            supports_pk_updates=True,
            supports_lobs=True,
            delivery_semantics=DeliverySemantics.AT_LEAST_ONCE,
        )

    def validate_prerequisites(self, source_config: Dict[str, Any]) -> Dict[str, Any]:
        binlog_format = source_config.get("binlog_format", "ROW")
        if binlog_format != "ROW":
            raise CDCPermissionError("MySQL prerequisite check failed: binlog_format must be 'ROW'")
        return {"binlog_format": "ROW", "status": "VALIDATED"}

    def start_capture(self, start_position: Optional[CDCSourcePosition] = None) -> None:
        conn = self.params.get("connection") or self.params.get("raw_connection") or self.params.get("stream_handle")
        if not conn and not self.params.get("event_stream"):
            from akaalEngine.cdc.models.errors import CDCCapabilityError
            raise CDCCapabilityError("MySQL binlog CDC physical stream cannot start: No physical database connection handle or stream reader provided in connection_params.")
        if isinstance(start_position, MySQLGTIDPosition):
            self.binlog_file = start_position.binlog_file
            self.binlog_pos = start_position.binlog_pos
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
            raise CDCCapabilityError("MySQL binlog CDC physical stream reader is not connected.")
        if hasattr(handle, "fetch_events"):
            return handle.fetch_events(max_events)
        elif hasattr(handle, "read_events"):
            return handle.read_events(max_events)
        elif hasattr(handle, "read"):
            return handle.read(max_events)
        return []

    def get_current_position(self) -> CDCSourcePosition:
        return MySQLGTIDPosition(self.binlog_file, self.binlog_pos)

    def close(self) -> None:
        self.is_active = False
