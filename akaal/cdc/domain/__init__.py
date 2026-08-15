"""
AKAAL CDC Domain Package — Platform Phase P3.1 Foundation
==========================================================
Canonical CDC domain models, source position abstractions, transaction boundaries,
consistency boundaries, session lifecycle state machines, and durability contracts.
"""

from akaal.cdc.domain.positions import (
    CDCSourcePosition,
    PostgresLSNPosition,
    MySQLGTIDPosition,
    OracleSCNPosition,
    MSSQLChangePosition,
    MongoDBOpLogPosition,
    parse_source_position,
)
from akaal.cdc.domain.events import (
    CDCOperationType,
    CDCTransactionBoundary,
    CDCEventIdentity,
    CDCEvent,
    CDCTransaction,
)
from akaal.cdc.domain.consistency import (
    CDCConsistencyBoundary,
    ConsistencyBoundaryState,
)
from akaal.cdc.domain.lifecycle import (
    CDCAckState,
    CDCSessionState,
    CDCSessionStateMachine,
    InvalidStateTransitionError,
)
from akaal.cdc.domain.durability import (
    CDCCheckpoint,
    CDCDurabilityContract,
)
from akaal.cdc.domain.errors import (
    CDCFailureCategory,
    CDCFailureType,
    CDCFailure,
    CDCExecutionError,
)
from akaal.cdc.domain.telemetry import (
    CDCMonitoringDTO,
)

__all__ = [
    "CDCSourcePosition",
    "PostgresLSNPosition",
    "MySQLGTIDPosition",
    "OracleSCNPosition",
    "MSSQLChangePosition",
    "MongoDBOpLogPosition",
    "parse_source_position",
    "CDCOperationType",
    "CDCTransactionBoundary",
    "CDCEventIdentity",
    "CDCEvent",
    "CDCTransaction",
    "CDCConsistencyBoundary",
    "ConsistencyBoundaryState",
    "CDCAckState",
    "CDCSessionState",
    "CDCSessionStateMachine",
    "InvalidStateTransitionError",
    "CDCCheckpoint",
    "CDCDurabilityContract",
    "CDCFailureCategory",
    "CDCFailureType",
    "CDCFailure",
    "CDCExecutionError",
    "CDCMonitoringDTO",
]
