"""
akaalEngine.cdc.models.capabilities
===================================
Enums & dataclasses defining CDC capabilities, handshake modes, ordering guarantees, and delivery semantics.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional


class MigrationMode(str, Enum):
    ONLINE_NATIVE_CDC = "ONLINE_NATIVE_CDC"
    ONLINE_CHANGE_STREAM = "ONLINE_CHANGE_STREAM"
    ONLINE_INCREMENTAL = "ONLINE_INCREMENTAL"
    QUIESCE_ASSISTED = "QUIESCE_ASSISTED"
    OFFLINE_SNAPSHOT = "OFFLINE_SNAPSHOT"


class HandshakeMode(str, Enum):
    ATOMIC_SNAPSHOT_CDC_HANDSHAKE = "ATOMIC_SNAPSHOT_CDC_HANDSHAKE"
    CONSISTENT_SNAPSHOT_WITH_LOG_POSITION = "CONSISTENT_SNAPSHOT_WITH_LOG_POSITION"
    BEST_EFFORT_HANDSHAKE = "BEST_EFFORT_HANDSHAKE"
    REQUIRES_SOURCE_WRITE_QUIESCE = "REQUIRES_SOURCE_WRITE_QUIESCE"
    OFFLINE_ONLY = "OFFLINE_ONLY"


class SynchronizationBarrierStrategy(str, Enum):
    LOG_MARKER_INJECTION = "LOG_MARKER_INJECTION"
    CAPTURED_POSITION_POST_QUIESCE = "CAPTURED_POSITION_POST_QUIESCE"
    TRANSACTION_COMMIT_BARRIER = "TRANSACTION_COMMIT_BARRIER"
    PROVIDER_NATIVE_WATERMARK = "PROVIDER_NATIVE_WATERMARK"
    QUIESCE_OFFLINE_REQUIRED = "QUIESCE_OFFLINE_REQUIRED"


class OrderingGuarantee(str, Enum):
    GLOBAL_COMMIT_ORDER = "GLOBAL_COMMIT_ORDER"
    PARTITION_ORDER = "PARTITION_ORDER"
    PER_KEY_ORDER = "PER_KEY_ORDER"
    PROVIDER_DEFINED = "PROVIDER_DEFINED"


class RetentionState(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    RETENTION_LOST = "RETENTION_LOST"
    UNKNOWN = "UNKNOWN"


class DeliverySemantics(str, Enum):
    EFFECTIVELY_ONCE_PROVEN = "EFFECTIVELY_ONCE_PROVEN"
    AT_LEAST_ONCE = "AT_LEAST_ONCE"
    PROVIDER_DEFINED = "PROVIDER_DEFINED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CDCCapabilityDescriptor:
    """Capability descriptor for a provider CDC source miner."""
    provider_name: str
    capture_mode: MigrationMode
    handshake_mode: HandshakeMode
    barrier_strategy: SynchronizationBarrierStrategy
    ordering_guarantee: OrderingGuarantee
    supports_transactions: bool = True
    supports_before_images: bool = True
    supports_ddl_capture: bool = False
    supports_pk_updates: bool = True
    supports_lobs: bool = True
    delivery_semantics: DeliverySemantics = DeliverySemantics.AT_LEAST_ONCE
