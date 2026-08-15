"""
AKAAL CDC Transactional Causality & Replay Ordering Domain Models (P3.7).
========================================================================
Identity-bound, strongly-typed, immutable causality and ordering data abstractions.
"""

import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Set
from akaal.cdc.domain.events import CDCEventIdentity, CDCTransaction
from akaal.cdc.domain.positions import CDCSourcePosition, parse_source_position


class CDCDependencyType(str, Enum):
    """Canonical classification for CDC transaction dependencies."""
    SAME_ENTITY = "SAME_ENTITY"
    SAME_PRIMARY_KEY = "SAME_PRIMARY_KEY"
    FOREIGN_KEY_PARENT_CHILD = "FOREIGN_KEY_PARENT_CHILD"
    FOREIGN_KEY_CHILD_PARENT = "FOREIGN_KEY_CHILD_PARENT"
    MULTI_TABLE_TRANSACTION = "MULTI_TABLE_TRANSACTION"
    TRANSACTION_SEQUENCE = "TRANSACTION_SEQUENCE"
    SCHEMA_DEPENDENCY = "SCHEMA_DEPENDENCY"
    DDL_DML_DEPENDENCY = "DDL_DML_DEPENDENCY"
    WRITE_AFTER_WRITE = "WRITE_AFTER_WRITE"
    WRITE_AFTER_DELETE = "WRITE_AFTER_DELETE"
    DELETE_AFTER_WRITE = "DELETE_AFTER_WRITE"
    INSERT_BEFORE_CHILD_INSERT = "INSERT_BEFORE_CHILD_INSERT"
    PARENT_DELETE_AFTER_CHILD_DELETE = "PARENT_DELETE_AFTER_CHILD_DELETE"
    CROSS_PARTITION_TRANSACTION = "CROSS_PARTITION_TRANSACTION"
    EXPLICIT_SOURCE_DEPENDENCY = "EXPLICIT_SOURCE_DEPENDENCY"
    UNKNOWN_DEPENDENCY = "UNKNOWN_DEPENDENCY"


class CDCReplayEligibility(str, Enum):
    """Authoritative replay eligibility decisions for transactions."""
    READY = "READY"
    BLOCKED_BY_DEPENDENCY = "BLOCKED_BY_DEPENDENCY"
    BLOCKED_BY_SCHEMA = "BLOCKED_BY_SCHEMA"
    BLOCKED_BY_CROSS_PARTITION_BARRIER = "BLOCKED_BY_CROSS_PARTITION_BARRIER"
    BLOCKED_BY_FENCING = "BLOCKED_BY_FENCING"
    BLOCKED_BY_UNRESOLVED_PREDECESSOR = "BLOCKED_BY_UNRESOLVED_PREDECESSOR"
    BLOCKED_BY_FAILED_PREDECESSOR = "BLOCKED_BY_FAILED_PREDECESSOR"
    BLOCKED_BY_AMBIGUOUS_CAUSALITY = "BLOCKED_BY_AMBIGUOUS_CAUSALITY"
    REJECTED_IDENTITY_MISMATCH = "REJECTED_IDENTITY_MISMATCH"
    REJECTED_STALE_GENERATION = "REJECTED_STALE_GENERATION"


class CDCDependencyResolutionState(str, Enum):
    """Lifecycle status of a transaction dependency."""
    UNRESOLVED = "UNRESOLVED"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CDCCausalIdentity:
    """Identity structure binding causal nodes to migration, job, run, session, and position."""

    def __init__(
        self,
        identity: CDCEventIdentity,
        transaction_id: str,
        routing_generation: int = 1,
        partition_id: int = 0,
        schema_version: str = "v1",
        fencing_epoch: int = 1,
        source_position: Optional[CDCSourcePosition] = None,
    ) -> None:
        self.identity = identity
        self.transaction_id = transaction_id
        self.routing_generation = routing_generation
        self.partition_id = partition_id
        self.schema_version = schema_version
        self.fencing_epoch = fencing_epoch
        self.source_position = source_position

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "transaction_id": self.transaction_id,
            "routing_generation": self.routing_generation,
            "partition_id": self.partition_id,
            "schema_version": self.schema_version,
            "fencing_epoch": self.fencing_epoch,
            "source_position": self.source_position.to_dict() if self.source_position else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CDCCausalIdentity":
        return cls(
            identity=CDCEventIdentity.from_dict(data["identity"]),
            transaction_id=data["transaction_id"],
            routing_generation=data.get("routing_generation", 1),
            partition_id=data.get("partition_id", 0),
            schema_version=data.get("schema_version", "v1"),
            fencing_epoch=data.get("fencing_epoch", 1),
            source_position=parse_source_position(data["source_position"]) if data.get("source_position") else None,
        )


class CDCDependencyEdge:
    """Directed dependency edge representing T1 -> T2 (T2 requires T1)."""

    def __init__(
        self,
        source_tx_id: str,
        target_tx_id: str,
        dependency_type: CDCDependencyType = CDCDependencyType.UNKNOWN_DEPENDENCY,
        description: str = "",
        is_satisfied: bool = False,
    ) -> None:
        self.source_tx_id = source_tx_id
        self.target_tx_id = target_tx_id
        self.dependency_type = dependency_type
        self.description = description
        self.is_satisfied = is_satisfied

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_tx_id": self.source_tx_id,
            "target_tx_id": self.target_tx_id,
            "dependency_type": self.dependency_type.value,
            "description": self.description,
            "is_satisfied": self.is_satisfied,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CDCDependencyEdge":
        return cls(
            source_tx_id=data["source_tx_id"],
            target_tx_id=data["target_tx_id"],
            dependency_type=CDCDependencyType(data.get("dependency_type", "UNKNOWN_DEPENDENCY")),
            description=data.get("description", ""),
            is_satisfied=data.get("is_satisfied", False),
        )


class CDCTransactionDependencySet:
    """Container holding set of dependency edges for a single transaction."""

    def __init__(self, tx_id: str, edges: Optional[List[CDCDependencyEdge]] = None) -> None:
        self.tx_id = tx_id
        self.edges = edges or []

    def add_edge(self, edge: CDCDependencyEdge) -> None:
        if not any(e.source_tx_id == edge.source_tx_id and e.target_tx_id == edge.target_tx_id for e in self.edges):
            self.edges.append(edge)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "edges": [e.to_dict() for e in self.edges],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CDCTransactionDependencySet":
        return cls(
            tx_id=data["tx_id"],
            edges=[CDCDependencyEdge.from_dict(e) for e in data.get("edges", [])],
        )


class CDCOrderingDecision:
    """Backend-authoritative ordering decision DTO for a transaction."""

    def __init__(
        self,
        tx_id: str,
        eligibility: CDCReplayEligibility,
        reason: str = "",
        blocker_tx_ids: Optional[List[str]] = None,
    ) -> None:
        self.tx_id = tx_id
        self.eligibility = eligibility
        self.reason = reason
        self.blocker_tx_ids = blocker_tx_ids or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "eligibility": self.eligibility.value,
            "reason": self.reason,
            "blocker_tx_ids": self.blocker_tx_ids,
        }


class CDCOrderingBarrierState:
    """State tracking active ordering barriers."""

    def __init__(
        self,
        barrier_id: str,
        cdc_session_id: str,
        tx_id: str,
        status: str = "ACTIVE",
        created_at: Optional[str] = None,
    ) -> None:
        self.barrier_id = barrier_id
        self.cdc_session_id = cdc_session_id
        self.tx_id = tx_id
        self.status = status
        self.created_at = created_at or datetime.datetime.now(datetime.timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "barrier_id": self.barrier_id,
            "cdc_session_id": self.cdc_session_id,
            "tx_id": self.tx_id,
            "status": self.status,
            "created_at": self.created_at,
        }


class CDCCausalityGraph:
    """Serializable causality graph state container."""

    def __init__(
        self,
        cdc_session_id: str,
        nodes: Optional[Dict[str, Dict[str, Any]]] = None,
        edges: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.cdc_session_id = cdc_session_id
        self.nodes = nodes or {}
        self.edges = edges or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cdc_session_id": self.cdc_session_id,
            "nodes": self.nodes,
            "edges": self.edges,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CDCCausalityGraph":
        return cls(
            cdc_session_id=data["cdc_session_id"],
            nodes=data.get("nodes", {}),
            edges=data.get("edges", []),
        )
