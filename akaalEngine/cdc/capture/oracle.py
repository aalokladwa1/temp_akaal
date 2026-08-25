"""
akaalEngine.cdc.capture.oracle
==============================
Oracle LogMiner & SCN CDC Source Capture Driver mined from `akaal/cdc/sources/oracle.py`.
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
from akaalEngine.cdc.models.position import CDCSourcePosition, OracleSCNPosition

logger = logging.getLogger("akaalEngine.cdc.capture.oracle")


class OracleCDCSourceAdapter(ICDCSourceAdapter):
    """Oracle LogMiner & SCN CDC Source Adapter."""

    def __init__(self, connection_params: Dict[str, Any]):
        self.params = connection_params
        self.current_scn = 100000
        self.is_active = False

    @property
    def engine_name(self) -> str:
        return "ORACLE"

    @property
    def capabilities(self) -> CDCCapabilityDescriptor:
        return CDCCapabilityDescriptor(
            provider_name="ORACLE",
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
        archivelog = source_config.get("archivelog", True)
        if not archivelog:
            raise CDCPermissionError("Oracle prerequisite check failed: ARCHIVELOG mode must be enabled")
        return {"archivelog": "ENABLED", "status": "VALIDATED"}

    def start_capture(self, start_position: Optional[CDCSourcePosition] = None) -> None:
        conn = self.params.get("connection") or self.params.get("raw_connection") or self.params.get("stream_handle")
        if not conn and not self.params.get("event_stream"):
            from akaalEngine.cdc.models.errors import CDCCapabilityError
            raise CDCCapabilityError("Oracle LogMiner CDC physical stream cannot start: No physical database connection handle or stream reader provided in connection_params.")
        if isinstance(start_position, OracleSCNPosition):
            self.current_scn = start_position.scn
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
            raise CDCCapabilityError("Oracle LogMiner CDC physical stream reader is not connected.")
        if hasattr(handle, "fetch_events"):
            return handle.fetch_events(max_events)
        elif hasattr(handle, "read_events"):
            return handle.read_events(max_events)
        elif hasattr(handle, "read"):
            return handle.read(max_events)
        return []

    def get_current_position(self) -> CDCSourcePosition:
        return OracleSCNPosition(self.current_scn)

    def close(self) -> None:
        self.is_active = False
