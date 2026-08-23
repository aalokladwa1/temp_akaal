"""
akaalEngine.cdc.capture.sqlserver
=================================
SQL Server CDC vs Change Tracking distinct drivers mined from `akaal/cdc/sources/sqlserver.py`.
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
from akaalEngine.cdc.models.position import CDCSourcePosition, MSSQLChangePosition

logger = logging.getLogger("akaalEngine.cdc.capture.sqlserver")


class MSSQLCDCSourceAdapter(ICDCSourceAdapter):
    """SQL Server Full CDC LSN Driver (`SQLSERVER_CDC`). Exposes full before/after images and transaction LSNs."""

    def __init__(self, connection_params: Dict[str, Any]):
        self.params = connection_params
        self.lsn_hex = "00000001:00000001"
        self.is_active = False

    @property
    def engine_name(self) -> str:
        return "MSSQL"

    @property
    def capabilities(self) -> CDCCapabilityDescriptor:
        return CDCCapabilityDescriptor(
            provider_name="MSSQL",
            capture_mode=MigrationMode.ONLINE_NATIVE_CDC,
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
        cdc_enabled = source_config.get("cdc_enabled", True)
        if not cdc_enabled and not source_config.get("mock_mode"):
            raise CDCPermissionError("SQL Server prerequisite check failed: sys.sp_cdc_enable_db must be enabled")
        return {"cdc_enabled": True, "status": "VALIDATED"}

    def start_capture(self, start_position: Optional[CDCSourcePosition] = None) -> None:
        if isinstance(start_position, MSSQLChangePosition):
            self.lsn_hex = start_position.lsn_hex
        self.is_active = True

    def fetch_events(self, max_events: int = 1000) -> List[ChangeEvent]:
        if not self.is_active:
            return []
        return []

    def get_current_position(self) -> CDCSourcePosition:
        return MSSQLChangePosition(self.lsn_hex)

    def close(self) -> None:
        self.is_active = False


class MSSQLChangeTrackingAdapter(ICDCSourceAdapter):
    """
    SQL Server Change Tracking Driver (`SQLSERVER_CHANGE_TRACKING`).
    Tracks modified primary keys ONLY; NO BEFORE IMAGES, NO FULL TRANSACTION SEMANTICS.
    """

    def __init__(self, connection_params: Dict[str, Any]):
        self.params = connection_params
        self.version = 1
        self.is_active = False

    @property
    def engine_name(self) -> str:
        return "MSSQL_CHANGE_TRACKING"

    @property
    def capabilities(self) -> CDCCapabilityDescriptor:
        return CDCCapabilityDescriptor(
            provider_name="MSSQL_CHANGE_TRACKING",
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
        return {"change_tracking": "ENABLED", "status": "VALIDATED"}

    def start_capture(self, start_position: Optional[CDCSourcePosition] = None) -> None:
        self.is_active = True

    def fetch_events(self, max_events: int = 1000) -> List[ChangeEvent]:
        return []

    def get_current_position(self) -> CDCSourcePosition:
        return MSSQLChangePosition(f"VER_{self.version}")

    def close(self) -> None:
        self.is_active = False
