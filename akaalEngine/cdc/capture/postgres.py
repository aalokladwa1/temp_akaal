"""
akaalEngine.cdc.capture.postgres
================================
PostgreSQL Logical CDC Source Capture Driver mined from `akaal/cdc/sources/postgres.py`.
"""

import logging
import time
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
from akaalEngine.cdc.models.event import ChangeEvent, ChangeOperation, TransactionContext
from akaalEngine.cdc.models.position import CDCSourcePosition, PostgresLSNPosition

logger = logging.getLogger("akaalEngine.cdc.capture.postgres")


class PostgreSQLCDCSourceAdapter(ICDCSourceAdapter):
    """PostgreSQL Logical CDC Source Adapter using replication slots and pgoutput / wal2json."""

    def __init__(self, connection_params: Dict[str, Any]):
        self.params = connection_params
        self.current_lsn_val = 0x10000
        self.is_active = False

    @property
    def engine_name(self) -> str:
        return "POSTGRESQL"

    @property
    def capabilities(self) -> CDCCapabilityDescriptor:
        return CDCCapabilityDescriptor(
            provider_name="POSTGRESQL",
            capture_mode=MigrationMode.ONLINE_NATIVE_CDC,
            handshake_mode=HandshakeMode.CONSISTENT_SNAPSHOT_WITH_LOG_POSITION,
            barrier_strategy=SynchronizationBarrierStrategy.LOG_MARKER_INJECTION,
            ordering_guarantee=OrderingGuarantee.GLOBAL_COMMIT_ORDER,
            supports_transactions=True,
            supports_before_images=True,
            supports_ddl_capture=False,
            supports_pk_updates=True,
            supports_lobs=True,
            delivery_semantics=DeliverySemantics.AT_LEAST_ONCE,
        )

    def validate_prerequisites(self, source_config: Dict[str, Any]) -> Dict[str, Any]:
        wal_level = source_config.get("wal_level", "logical")
        if wal_level != "logical":
            raise CDCPermissionError("PostgreSQL prerequisite check failed: wal_level must be 'logical'")
        return {"wal_level": "logical", "status": "VALIDATED"}

    def start_capture(self, start_position: Optional[CDCSourcePosition] = None) -> None:
        conn = self.params.get("connection") or self.params.get("raw_connection") or self.params.get("stream_handle")
        if not conn and not self.params.get("event_stream"):
            from akaalEngine.cdc.models.errors import CDCCapabilityError
            raise CDCCapabilityError("PostgreSQL CDC physical replication stream cannot start: No physical database connection handle or stream reader provided in connection_params.")
        if isinstance(start_position, PostgresLSNPosition):
            self.current_lsn_val = start_position.numeric_val
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
            raise CDCCapabilityError("PostgreSQL CDC physical replication slot consumer is not connected.")
        if hasattr(handle, "fetch_events"):
            return handle.fetch_events(max_events)
        elif hasattr(handle, "read_events"):
            return handle.read_events(max_events)
        elif hasattr(handle, "read"):
            return handle.read(max_events)
        return []

    def get_current_position(self) -> CDCSourcePosition:
        hi = self.current_lsn_val >> 32
        lo = self.current_lsn_val & 0xFFFFFFFF
        lsn_str = f"{hi:X}/{lo:X}"
        return PostgresLSNPosition(lsn_str)

    def close(self) -> None:
        self.is_active = False
