"""
AKAAL CDC Multi-Master & Bidirectional Replication Package.
=============================================================
Provides bidirectional topology management, origin loop filtering, multi-master conflict detection,
deterministic conflict resolution, and entity quarantine.
"""

from akaal.cdc.multi_master.domain import (
    CDCReplicationTopologyState,
    CDCReplicationDirection,
    CDCDirectionState,
    CDCReplicationTopology,
    CDCOriginProvenance,
    CDCConflictType,
    CDCConflictState,
    CDCConflictResolutionPolicy,
    CDCConflictRecord,
    CDCConflictResolutionDecision,
    CDCQuarantineState,
    CDCQuarantineRecord,
)
from akaal.cdc.multi_master.loop_filter import CDCReplicationLoopFilter
from akaal.cdc.multi_master.conflict_detector import CDCConflictDetector
from akaal.cdc.multi_master.resolver import CDCConflictResolver
from akaal.cdc.multi_master.quarantine import CDCConflictQuarantineManager
from akaal.cdc.multi_master.topology import CDCBirectionalTopologyManager

__all__ = [
    "CDCReplicationTopologyState",
    "CDCReplicationDirection",
    "CDCDirectionState",
    "CDCReplicationTopology",
    "CDCOriginProvenance",
    "CDCConflictType",
    "CDCConflictState",
    "CDCConflictResolutionPolicy",
    "CDCConflictRecord",
    "CDCConflictResolutionDecision",
    "CDCQuarantineState",
    "CDCQuarantineRecord",
    "CDCReplicationLoopFilter",
    "CDCConflictDetector",
    "CDCConflictResolver",
    "CDCConflictQuarantineManager",
    "CDCBirectionalTopologyManager",
]
