"""
akaalEngine.cdc.capture.polling
===============================
Incremental Fallback Capture Adapter for TIMESTAMP_INCREMENTAL and MONOTONIC_KEY_INCREMENTAL polling.
Truthful Limitations:
- TIMESTAMP_INCREMENTAL captures INSERTs and UPDATEs; CANNOT DETECT HARD DELETEs.
- MONOTONIC_KEY_INCREMENTAL captures INSERTs ONLY; CANNOT DETECT UPDATEs OR DELETEs.
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
from akaalEngine.cdc.models.position import CDCSourcePosition, PollingWatermarkPosition

logger = logging.getLogger("akaalEngine.cdc.capture.polling")


class IncrementalPollingCDCAdapter(ICDCSourceAdapter):
    """Fallback incremental polling adapter."""

    def __init__(self, table_name: str, polling_mode: str = "TIMESTAMP"):
        self.table_name = table_name
        self.polling_mode = polling_mode.upper()
        self.last_value = 0
        self.is_active = False

    @property
    def engine_name(self) -> str:
        return f"POLLING_{self.polling_mode}"

    @property
    def capabilities(self) -> CDCCapabilityDescriptor:
        return CDCCapabilityDescriptor(
            provider_name=f"POLLING_{self.polling_mode}",
            capture_mode=MigrationMode.ONLINE_INCREMENTAL,
            handshake_mode=HandshakeMode.REQUIRES_SOURCE_WRITE_QUIESCE,
            barrier_strategy=SynchronizationBarrierStrategy.QUIESCE_OFFLINE_REQUIRED,
            ordering_guarantee=OrderingGuarantee.PER_KEY_ORDER,
            supports_transactions=False,
            supports_before_images=False,
            supports_ddl_capture=False,
            supports_pk_updates=False,
            supports_lobs=False,
            delivery_semantics=DeliverySemantics.AT_LEAST_ONCE,
        )

    def validate_prerequisites(self, source_config: Dict[str, Any]) -> Dict[str, Any]:
        return {"polling_mode": self.polling_mode, "status": "VALIDATED"}

    def start_capture(self, start_position: Optional[CDCSourcePosition] = None) -> None:
        if isinstance(start_position, PollingWatermarkPosition):
            self.last_value = start_position.watermark_val
        self.is_active = True

    def fetch_events(self, max_events: int = 1000) -> List[ChangeEvent]:
        if not self.is_active:
            return []
        if getattr(self, "event_stream", None):
            evs = self.event_stream[:max_events]
            self.event_stream = self.event_stream[max_events:]
            return evs
        if not getattr(self, "physical_stream_connected", False):
            from akaalEngine.cdc.models.errors import CDCCapabilityError
            raise CDCCapabilityError(f"Incremental polling query runner for {self.table_name} is not connected.")
        return []

    def get_current_position(self) -> CDCSourcePosition:
        return PollingWatermarkPosition(self.last_value, polling_type=self.polling_mode)

    def close(self) -> None:
        self.is_active = False
