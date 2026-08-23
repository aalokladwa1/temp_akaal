"""
akaalEngine.discovery.models
============================
Immutable physical fact models and DTOs for Authority #3 Discovery.
"""

from akaalEngine.discovery.models.cdc import (
    CDCMechanism,
    CDCPrerequisiteSnapshot,
    StartingCommitPosition,
)
from akaalEngine.discovery.models.context import (
    DiscoveryContext,
    DiscoveryDepth,
    DiscoveryScope,
)
from akaalEngine.discovery.models.environment import (
    CharsetFacts,
    CollationFacts,
    ConfigurationFacts,
    EnvironmentFacts,
    LimitsFacts,
    TimezoneFacts,
)
from akaalEngine.discovery.models.identity import (
    DiscoveredEndpointIdentity,
    EngineEdition,
    ServerVersion,
)
from akaalEngine.discovery.models.inventory import (
    NamespaceInventory,
    ObjectClassification,
    ObjectInventory,
    ObjectInventoryPage,
    ObjectType,
    TableFacts,
    ViewFacts,
)
from akaalEngine.discovery.models.partitioning import (
    PartitionBoundFacts,
    PartitionFacts,
    PartitionStrategy,
    SubpartitionFacts,
    TokenRangeFacts,
)
from akaalEngine.discovery.models.permissions import (
    PermissionAssessment,
    PrivilegeFact,
    ThreeStatePermission,
)
from akaalEngine.discovery.models.programmables import (
    ProgrammableInventory,
    RoutineFacts,
    RoutineParameterFacts,
    RoutineType,
    SequenceFacts,
    TriggerFacts,
    TriggerTiming,
    UDTFacts,
)
from akaalEngine.discovery.models.sampling import (
    InferredDocumentShape,
    SampledFieldObservation,
    SampledRecordSet,
)
from akaalEngine.discovery.models.snapshot import (
    DiscoveryCompleteness,
    DiscoveryFingerprint,
    DiscoverySnapshot,
)
from akaalEngine.discovery.models.statistics import (
    ColumnCardinalityFacts,
    CountAccuracy,
    StatisticsSnapshot,
    TableSizeFacts,
)
from akaalEngine.discovery.models.structure import (
    CheckConstraintFacts,
    ColumnPhysicalMetadata,
    ConstraintType,
    ForeignKeyFacts,
    IndexAccessMethod,
    IndexFacts,
    ObjectStructureFacts,
    PrimaryKeyFacts,
    UniqueConstraintFacts,
)
from akaalEngine.discovery.models.topology import (
    ClusterNodeFacts,
    NodeRole,
    TopologySnapshot,
)
from akaalEngine.discovery.models.volume import (
    LargestObjectItem,
    LOBVolumeFacts,
    VolumeSnapshot,
)

__all__ = [
    # Context
    "DiscoveryDepth",
    "DiscoveryScope",
    "DiscoveryContext",
    # Identity
    "ServerVersion",
    "EngineEdition",
    "DiscoveredEndpointIdentity",
    # Inventory
    "ObjectClassification",
    "ObjectType",
    "TableFacts",
    "ViewFacts",
    "NamespaceInventory",
    "ObjectInventory",
    "ObjectInventoryPage",
    # Structure
    "ConstraintType",
    "IndexAccessMethod",
    "ColumnPhysicalMetadata",
    "PrimaryKeyFacts",
    "ForeignKeyFacts",
    "UniqueConstraintFacts",
    "CheckConstraintFacts",
    "IndexFacts",
    "ObjectStructureFacts",
    # Programmables
    "RoutineType",
    "TriggerTiming",
    "RoutineParameterFacts",
    "RoutineFacts",
    "TriggerFacts",
    "SequenceFacts",
    "UDTFacts",
    "ProgrammableInventory",
    # Partitioning
    "PartitionStrategy",
    "PartitionBoundFacts",
    "SubpartitionFacts",
    "TokenRangeFacts",
    "PartitionFacts",
    # Statistics
    "CountAccuracy",
    "TableSizeFacts",
    "ColumnCardinalityFacts",
    "StatisticsSnapshot",
    # Volume
    "LargestObjectItem",
    "LOBVolumeFacts",
    "VolumeSnapshot",
    # Permissions
    "ThreeStatePermission",
    "PrivilegeFact",
    "PermissionAssessment",
    # Topology
    "NodeRole",
    "ClusterNodeFacts",
    "TopologySnapshot",
    # CDC
    "CDCMechanism",
    "StartingCommitPosition",
    "CDCPrerequisiteSnapshot",
    # Environment
    "CharsetFacts",
    "CollationFacts",
    "TimezoneFacts",
    "LimitsFacts",
    "ConfigurationFacts",
    # Sampling
    "SampledFieldObservation",
    "InferredDocumentShape",
    "SampledRecordSet",
    # Snapshot
    "DiscoveryCompleteness",
    "DiscoveryFingerprint",
    "DiscoverySnapshot",
]
