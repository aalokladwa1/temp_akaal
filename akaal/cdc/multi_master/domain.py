"""
AKAAL CDC Multi-Master & Bidirectional Domain Models.
=====================================================
Strongly typed domain models for CDC bidirectional replication topology, origin provenance,
conflict classification, quarantine tracking, and deterministic resolution decisions.
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
import datetime


class CDCReplicationTopologyState(str, Enum):
    """Lifecycle states for bidirectional CDC replication topology."""
    CREATED = "CREATED"
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    QUIESCED = "QUIESCED"
    DEGRADED = "DEGRADED"
    RECOVERING = "RECOVERING"
    FAILED = "FAILED"
    TERMINATED = "TERMINATED"


class CDCReplicationDirection(str, Enum):
    """Replication direction classification."""
    A_TO_B = "A_TO_B"
    B_TO_A = "B_TO_A"
    BIDIRECTIONAL = "BIDIRECTIONAL"


@dataclass
class CDCDirectionState:
    """Status telemetry and position tracker for a single replication direction."""
    direction_id: str
    source_database_id: str
    target_database_id: str
    cdc_session_id: str
    capture_state: str = "IDLE"
    apply_state: str = "IDLE"
    captured_position: Optional[str] = None
    applied_position: Optional[str] = None
    acknowledged_position: Optional[str] = None
    lag_ms: float = 0.0
    backlog_count: int = 0
    last_event_at: Optional[str] = None
    health: str = "HEALTHY"
    fencing_epoch: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CDCDirectionState':
        return cls(**data)


@dataclass
class CDCReplicationTopology:
    """Identity-bound canonical CDC replication topology."""
    topology_id: str
    migration_id: str
    job_id: str
    run_id: str
    source_a_database_id: str
    source_b_database_id: str
    cdc_session_a_to_b: str
    cdc_session_b_to_a: str
    state: CDCReplicationTopologyState = CDCReplicationTopologyState.CREATED
    direction_a_to_b: Optional[CDCDirectionState] = None
    direction_b_to_a: Optional[CDCDirectionState] = None
    designated_primary_database_id: Optional[str] = None
    fencing_epoch: int = 1
    created_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["state"] = self.state.value if isinstance(self.state, Enum) else self.state
        if self.direction_a_to_b:
            res["direction_a_to_b"] = self.direction_a_to_b.to_dict()
        if self.direction_b_to_a:
            res["direction_b_to_a"] = self.direction_b_to_a.to_dict()
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CDCReplicationTopology':
        d = dict(data)
        if "state" in d and isinstance(d["state"], str):
            d["state"] = CDCReplicationTopologyState(d["state"])
        if "direction_a_to_b" in d and isinstance(d["direction_a_to_b"], dict):
            d["direction_a_to_b"] = CDCDirectionState.from_dict(d["direction_a_to_b"])
        if "direction_b_to_a" in d and isinstance(d["direction_b_to_a"], dict):
            d["direction_b_to_a"] = CDCDirectionState.from_dict(d["direction_b_to_a"])
        return cls(**d)


@dataclass
class CDCOriginProvenance:
    """Canonical origin provenance tag attached to events/transactions."""
    origin_database_id: str
    origin_topology_id: str
    origin_run_id: str
    akaal_writer_id: str
    replication_direction: str
    hop_count: int = 1
    origin_tx_id: Optional[str] = None
    origin_timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CDCOriginProvenance':
        return cls(**data)


class CDCConflictType(str, Enum):
    """Multi-master concurrent conflict classifications."""
    UPDATE_UPDATE = "UPDATE_UPDATE"
    UPDATE_DELETE = "UPDATE_DELETE"
    DELETE_UPDATE = "DELETE_UPDATE"
    INSERT_INSERT = "INSERT_INSERT"
    DELETE_DELETE = "DELETE_DELETE"
    INSERT_UPDATE = "INSERT_UPDATE"
    UPDATE_INSERT = "UPDATE_INSERT"


class CDCConflictState(str, Enum):
    """Lifecycle states of detected multi-master conflict."""
    DETECTED = "DETECTED"
    QUARANTINED = "QUARANTINED"
    EVALUATING = "EVALUATING"
    AUTO_RESOLUTION_SELECTED = "AUTO_RESOLUTION_SELECTED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    RESOLUTION_APPROVED = "RESOLUTION_APPROVED"
    APPLYING_RESOLUTION = "APPLYING_RESOLUTION"
    RESOLVED = "RESOLVED"
    RELEASED = "RELEASED"
    FAILED = "FAILED"


class CDCConflictResolutionPolicy(str, Enum):
    """Supported deterministic conflict resolution policies."""
    SOURCE_A_WINS = "SOURCE_A_WINS"
    SOURCE_B_WINS = "SOURCE_B_WINS"
    DESIGNATED_PRIMARY_WINS = "DESIGNATED_PRIMARY_WINS"
    LATEST_VERSION_WINS = "LATEST_VERSION_WINS"
    MANUAL_GOVERNANCE_REQUIRED = "MANUAL_GOVERNANCE_REQUIRED"


@dataclass
class CDCConflictRecord:
    """Identity-bound conflict record."""
    conflict_id: str
    topology_id: str
    migration_id: str
    job_id: str
    run_id: str
    entity_table: str
    entity_key: str
    source_a_tx_id: str
    source_b_tx_id: str
    source_a_position: str
    source_b_position: str
    conflict_type: CDCConflictType
    conflict_state: CDCConflictState = CDCConflictState.DETECTED
    schema_version: str = "v1.0"
    causal_evidence_ref: Optional[str] = None
    detected_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["conflict_type"] = self.conflict_type.value if isinstance(self.conflict_type, Enum) else self.conflict_type
        res["conflict_state"] = self.conflict_state.value if isinstance(self.conflict_state, Enum) else self.conflict_state
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CDCConflictRecord':
        d = dict(data)
        if "conflict_type" in d and isinstance(d["conflict_type"], str):
            d["conflict_type"] = CDCConflictType(d["conflict_type"])
        if "conflict_state" in d and isinstance(d["conflict_state"], str):
            d["conflict_state"] = CDCConflictState(d["conflict_state"])
        return cls(**d)


@dataclass
class CDCConflictResolutionDecision:
    """Identity-bound conflict resolution decision."""
    resolution_id: str
    conflict_id: str
    topology_id: str
    migration_id: str
    run_id: str
    policy: CDCConflictResolutionPolicy
    selected_winner: str  # "SOURCE_A", "SOURCE_B", "DESIGNATED_PRIMARY"
    decision_reason: str
    decision_evidence: Dict[str, Any]
    fencing_epoch: int
    decision_state: str = "APPROVED"
    decided_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["policy"] = self.policy.value if isinstance(self.policy, Enum) else self.policy
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CDCConflictResolutionDecision':
        d = dict(data)
        if "policy" in d and isinstance(d["policy"], str):
            d["policy"] = CDCConflictResolutionPolicy(d["policy"])
        return cls(**d)


class CDCQuarantineState(str, Enum):
    """Quarantine state lifecycle for an entity key."""
    ACTIVE = "ACTIVE"
    AWAITING_MANUAL_DECISION = "AWAITING_MANUAL_DECISION"
    RESOLUTION_PENDING = "RESOLUTION_PENDING"
    RESOLVED = "RESOLVED"
    RELEASE_PENDING = "RELEASE_PENDING"
    RELEASED = "RELEASED"
    FAILED = "FAILED"


@dataclass
class CDCQuarantineRecord:
    """Identity-bound quarantine record holding an entity key."""
    quarantine_id: str
    conflict_id: str
    topology_id: str
    migration_id: str
    run_id: str
    entity_table: str
    entity_key: str
    reason: str
    fencing_epoch: int
    state: CDCQuarantineState = CDCQuarantineState.ACTIVE
    resolution_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    released_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["state"] = self.state.value if isinstance(self.state, Enum) else self.state
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CDCQuarantineRecord':
        d = dict(data)
        if "state" in d and isinstance(d["state"], str):
            d["state"] = CDCQuarantineState(d["state"])
        return cls(**d)
