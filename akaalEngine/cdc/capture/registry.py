"""
akaalEngine.cdc.capture.registry
=================================
Dynamic provider -> ICDCSourceAdapter registry for Authority #10 CDC Capture.
Enables extensible, non-hardcoded provider resolution for M2 (Bulk + CDC) and M3 (CDC).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Type

from akaalEngine.cdc.capture.base import ICDCSourceAdapter
from akaalEngine.cdc.capture.mongodb import MongoDBCDCSourceAdapter
from akaalEngine.cdc.capture.mysql import MySQLCDCSourceAdapter
from akaalEngine.cdc.capture.oracle import OracleCDCSourceAdapter
from akaalEngine.cdc.capture.polling import IncrementalPollingCDCAdapter
from akaalEngine.cdc.capture.postgres import PostgreSQLCDCSourceAdapter
from akaalEngine.cdc.capture.sqlserver import MSSQLCDCSourceAdapter, MSSQLChangeTrackingAdapter
from akaalEngine.cdc.models.errors import CDCCapabilityError

logger = logging.getLogger("akaalEngine.cdc.capture.registry")


class CDCSourceAdapterRegistry:
    """Dynamic, provider-aware registry for CDC source adapters."""

    def __init__(self) -> None:
        self._adapters: Dict[str, Type[ICDCSourceAdapter]] = {}

    def register(self, provider_id: str, adapter_cls: Type[ICDCSourceAdapter]) -> None:
        pid = provider_id.strip().lower()
        self._adapters[pid] = adapter_cls

    def get(self, provider_id: str) -> Optional[Type[ICDCSourceAdapter]]:
        pid = provider_id.strip().lower()
        return self._adapters.get(pid)

    def is_registered(self, provider_id: str) -> bool:
        return provider_id.strip().lower() in self._adapters

    def list_providers(self) -> list[str]:
        return sorted(self._adapters.keys())

    def create_adapter(self, provider_id: str, connection_params: Dict[str, Any]) -> ICDCSourceAdapter:
        pid = provider_id.strip().lower()
        cls = self.get(pid)
        if cls is None:
            raise CDCCapabilityError(
                f"Provider '{provider_id}' does not support M2 CDC capture. "
                f"Static/file/non-stream providers are not eligible for M2. "
                f"Registered CDC providers: {self.list_providers()}"
            )
        return cls(connection_params)


default_cdc_source_adapter_registry = CDCSourceAdapterRegistry()

# Register standard providers dynamically
default_cdc_source_adapter_registry.register("mysql", MySQLCDCSourceAdapter)
default_cdc_source_adapter_registry.register("mariadb", MySQLCDCSourceAdapter)
default_cdc_source_adapter_registry.register("postgres", PostgreSQLCDCSourceAdapter)
default_cdc_source_adapter_registry.register("postgresql", PostgreSQLCDCSourceAdapter)
default_cdc_source_adapter_registry.register("cockroachdb", PostgreSQLCDCSourceAdapter)
default_cdc_source_adapter_registry.register("yugabytedb", PostgreSQLCDCSourceAdapter)
default_cdc_source_adapter_registry.register("oracle", OracleCDCSourceAdapter)
default_cdc_source_adapter_registry.register("orcl", OracleCDCSourceAdapter)
default_cdc_source_adapter_registry.register("mssql", MSSQLCDCSourceAdapter)
default_cdc_source_adapter_registry.register("sqlserver", MSSQLCDCSourceAdapter)
default_cdc_source_adapter_registry.register("mssql_change_tracking", MSSQLChangeTrackingAdapter)
default_cdc_source_adapter_registry.register("sqlserver_change_tracking", MSSQLChangeTrackingAdapter)
default_cdc_source_adapter_registry.register("mongodb", MongoDBCDCSourceAdapter)
default_cdc_source_adapter_registry.register("mongo", MongoDBCDCSourceAdapter)
default_cdc_source_adapter_registry.register("sqlite", IncrementalPollingCDCAdapter)
default_cdc_source_adapter_registry.register("polling", IncrementalPollingCDCAdapter)
default_cdc_source_adapter_registry.register("generic_polling", IncrementalPollingCDCAdapter)


def register_cdc_adapter(provider_id: str, adapter_cls: Type[ICDCSourceAdapter]) -> None:
    default_cdc_source_adapter_registry.register(provider_id, adapter_cls)
