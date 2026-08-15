"""
AKAAL CDC Sharding & Partition Routing Domain Models (P3.6).
============================================================
Identity-bound, generation-aware, strongly-typed sharding data models.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
import datetime
from akaal.cdc.domain.events import CDCEventIdentity, CDCTransaction
from akaal.cdc.domain.positions import CDCSourcePosition


class CDCBoundaryStatus(str, Enum):
    IDLE = "IDLE"
    RESERVED = "RESERVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"


class CDCPartitionKey:
    """Identity-bound partition key binding entity to logical partition."""

    def __init__(
        self,
        identity: CDCEventIdentity,
        table_name: str,
        entity_key: str,
        partition_id: int,
        routing_generation: int,
    ) -> None:
        self.identity = identity
        self.table_name = table_name
        self.entity_key = str(entity_key)
        self.partition_id = partition_id
        self.routing_generation = routing_generation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "table_name": self.table_name,
            "entity_key": self.entity_key,
            "partition_id": self.partition_id,
            "routing_generation": self.routing_generation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CDCPartitionKey":
        return cls(
            identity=CDCEventIdentity.from_dict(data["identity"]),
            table_name=data["table_name"],
            entity_key=data["entity_key"],
            partition_id=data["partition_id"],
            routing_generation=data["routing_generation"],
        )


class CDCRoutedTransaction:
    """Routed wrapper around CDCTransaction containing partition assignment metadata."""

    def __init__(
        self,
        transaction: CDCTransaction,
        partition_ids: List[int],
        routing_generation: int,
        is_multi_partition: bool = False,
    ) -> None:
        self.transaction = transaction
        self.partition_ids = sorted(list(set(partition_ids)))
        self.routing_generation = routing_generation
        self.is_multi_partition = is_multi_partition or len(self.partition_ids) > 1
        self.primary_partition_id = self.partition_ids[0] if self.partition_ids else 0

    @property
    def tx_id(self) -> str:
        return self.transaction.tx_id

    @property
    def commit_position(self) -> CDCSourcePosition:
        return self.transaction.commit_position

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction": self.transaction.to_dict(),
            "partition_ids": self.partition_ids,
            "routing_generation": self.routing_generation,
            "is_multi_partition": self.is_multi_partition,
            "primary_partition_id": self.primary_partition_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CDCRoutedTransaction":
        return cls(
            transaction=CDCTransaction.from_dict(data["transaction"]),
            partition_ids=data["partition_ids"],
            routing_generation=data["routing_generation"],
            is_multi_partition=data.get("is_multi_partition", False),
        )


class CDCRouteGeneration:
    """Topology version metadata representing a routing generation."""

    def __init__(
        self,
        routing_generation: int,
        partition_count: int,
        cdc_session_id: str,
        status: str = "ACTIVE",
        created_at: Optional[str] = None,
    ) -> None:
        self.routing_generation = routing_generation
        self.partition_count = partition_count
        self.cdc_session_id = cdc_session_id
        self.status = status
        self.created_at = created_at or datetime.datetime.now(datetime.timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "routing_generation": self.routing_generation,
            "partition_count": self.partition_count,
            "cdc_session_id": self.cdc_session_id,
            "status": self.status,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CDCRouteGeneration":
        return cls(
            routing_generation=data["routing_generation"],
            partition_count=data["partition_count"],
            cdc_session_id=data["cdc_session_id"],
            status=data.get("status", "ACTIVE"),
            created_at=data.get("created_at"),
        )


class CDCPartitionState:
    """Runtime status of a partition worker queue."""

    def __init__(
        self,
        partition_id: int,
        routing_generation: int,
        owner_worker_id: str,
        fencing_epoch: int,
        queue_depth: int = 0,
        oldest_position: Optional[str] = None,
        active_tx_count: int = 0,
        barrier_state: str = "IDLE",
        rebalance_state: str = "STABLE",
    ) -> None:
        self.partition_id = partition_id
        self.routing_generation = routing_generation
        self.owner_worker_id = owner_worker_id
        self.fencing_epoch = fencing_epoch
        self.queue_depth = queue_depth
        self.oldest_position = oldest_position
        self.active_tx_count = active_tx_count
        self.barrier_state = barrier_state
        self.rebalance_state = rebalance_state

    def to_dict(self) -> Dict[str, Any]:
        return {
            "partition_id": self.partition_id,
            "routing_generation": self.routing_generation,
            "owner_worker_id": self.owner_worker_id,
            "fencing_epoch": self.fencing_epoch,
            "queue_depth": self.queue_depth,
            "oldest_position": self.oldest_position,
            "active_tx_count": self.active_tx_count,
            "barrier_state": self.barrier_state,
            "rebalance_state": self.rebalance_state,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CDCPartitionState":
        return cls(
            partition_id=data["partition_id"],
            routing_generation=data["routing_generation"],
            owner_worker_id=data["owner_worker_id"],
            fencing_epoch=data["fencing_epoch"],
            queue_depth=data.get("queue_depth", 0),
            oldest_position=data.get("oldest_position"),
            active_tx_count=data.get("active_tx_count", 0),
            barrier_state=data.get("barrier_state", "IDLE"),
            rebalance_state=data.get("rebalance_state", "STABLE"),
        )
