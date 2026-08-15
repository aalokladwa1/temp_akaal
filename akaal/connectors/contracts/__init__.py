"""
AKAAL Universal Connector Contracts Package (P4.1).
===================================================
Exports all canonical base connector and capability extension interfaces.
"""

from akaal.connectors.contracts.base import (
    IUniversalConnector,
    ConnectionTestResult,
    HealthStatus,
)
from akaal.connectors.contracts.database import IDatabaseCapability
from akaal.connectors.contracts.document import IDocumentCapability
from akaal.connectors.contracts.warehouse import IWarehouseCapability
from akaal.connectors.contracts.streaming import IStreamingCapability
from akaal.connectors.contracts.object_storage import IObjectStorageCapability
from akaal.connectors.contracts.wide_column import IWideColumnCapability
from akaal.connectors.contracts.graph import IGraphCapability, IKeyValueCapability, ISearchCapability
from akaal.connectors.contracts.cloud_provider import ICloudProviderCapability

__all__ = [
    "IUniversalConnector",
    "ConnectionTestResult",
    "HealthStatus",
    "IDatabaseCapability",
    "IDocumentCapability",
    "IWarehouseCapability",
    "IStreamingCapability",
    "IObjectStorageCapability",
    "IWideColumnCapability",
    "IGraphCapability",
    "IKeyValueCapability",
    "ISearchCapability",
    "ICloudProviderCapability",
]
