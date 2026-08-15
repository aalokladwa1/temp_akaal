"""
AKAAL Universal Connectors Subsystem (P4.1).
============================================
Canonical connectivity layer defining universal connector contracts, capability manifests,
connection profiles, semantic compatibility, and extension contracts.
"""

from akaal.connectors.taxonomy import (
    ConnectorFamily,
    ConnectorRole,
    AuthenticationMechanism,
    ProofLevel,
    CapabilitySupportStatus,
    ConnectorErrorCategory,
    SemanticCompatibility,
)
from akaal.connectors.manifest import UniversalCapabilityManifest
from akaal.connectors.profile import ConnectionProfile
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
from akaal.connectors.compatibility import SemanticCompatibilityMatrix
from akaal.connectors.registry import UniversalConnectorRegistry
from akaal.connectors.bridge import LegacyAdapterUniversalBridge

__all__ = [
    "ConnectorFamily",
    "ConnectorRole",
    "AuthenticationMechanism",
    "ProofLevel",
    "CapabilitySupportStatus",
    "ConnectorErrorCategory",
    "SemanticCompatibility",
    "UniversalCapabilityManifest",
    "ConnectionProfile",
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
    "SemanticCompatibilityMatrix",
    "UniversalConnectorRegistry",
    "LegacyAdapterUniversalBridge",
]
