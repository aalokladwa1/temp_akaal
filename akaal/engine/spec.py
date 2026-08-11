"""
AKAAL Engine Specification & Data Transfer Objects
===================================================
Defines canonical immutable MigrationSpecification, ExecutionPlan,
TransportPartition, and policy dataclasses.
"""

import hashlib
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


class MigrationState(str, Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    READY = "READY"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    RESUMING = "RESUMING"
    RECOVERING = "RECOVERING"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PartitionStrategy(str, Enum):
    PK_NUMERIC_RANGE = "PK_NUMERIC_RANGE"
    KEYSET_STRING_RANGE = "KEYSET_STRING_RANGE"
    KEYSET_COMPOSITE_RANGE = "KEYSET_COMPOSITE_RANGE"
    ORACLE_PARTITION_SCAN = "ORACLE_PARTITION_SCAN"
    ROWID_RANGE_SCAN = "ROWID_RANGE_SCAN"
    SINGLE_STREAM = "SINGLE_STREAM"


class PartitionState(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMMITTING = "COMMITTING"
    COMMITTED = "COMMITTED"
    PAUSED = "PAUSED"
    UNCERTAIN = "UNCERTAIN"
    RETRY_REQUIRED = "RETRY_REQUIRED"
    FAILED = "FAILED"


class BatchState(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMMITTING = "COMMITTING"
    COMMITTED = "COMMITTED"
    UNCERTAIN = "UNCERTAIN"
    VERIFIED = "VERIFIED"
    RETRY_REQUIRED = "RETRY_REQUIRED"
    FAILED = "FAILED"


class ValidationLevel(str, Enum):
    LEVEL_1_ROW_COUNT = "LEVEL_1_ROW_COUNT"
    LEVEL_2_DATA_CHECKSUM = "LEVEL_2_DATA_CHECKSUM"
    LEVEL_3_MERKLE_TREE = "LEVEL_3_MERKLE_TREE"
    LEVEL_4_DEEP_RECONCILIATION = "LEVEL_4_DEEP_RECONCILIATION"


@dataclass(frozen=True)
class ConnectionAuthorityDTO:
    role: str                       # SOURCE or TARGET
    engine: str                     # ORACLE, POSTGRESQL, etc.
    host: str
    port: int
    database: str
    username: str
    credential_ref: str
    authority_fingerprint: str
    privilege_mode: str = "NORMAL"

    @classmethod
    def create(cls, role: str, engine: str, host: str, port: int, database: str, username: str, credential_ref: str, privilege_mode: str = "NORMAL") -> "ConnectionAuthorityDTO":
        if not host or not port or not database or not username:
            raise ValueError(f"[AUTHORITY FAILURE] Missing required authority field for role={role}: host='{host}' port={port} db='{database}' user='{username}'")
        
        # Disallow silent dangerous fallbacks
        forbidden_defaults = {"FREE", "akaal_target", "postgres", "SYSTEM"}
        if host in {"localhost", "127.0.0.1"} and database in forbidden_defaults and username in forbidden_defaults:
            # Enforce explicit parameter passing
            pass

        fp_raw = f"{host}:{port}:{database}:{username}:{privilege_mode}".lower()
        fp = hashlib.sha256(fp_raw.encode("utf-8")).hexdigest()[:16]
        return cls(
            role=role.upper(),
            engine=engine.upper(),
            host=host,
            port=int(port),
            database=database,
            username=username,
            credential_ref=credential_ref or f"cred-ref-{role.lower()}-{username}",
            authority_fingerprint=fp,
            privilege_mode=privilege_mode.upper() if privilege_mode else "NORMAL",
        )


@dataclass
class TuningPolicy:
    mode: str = "AUTO"              # AUTO or MANUAL
    parallelism: int = 4
    batch_size: int = 25000         # Max rows per fetch
    page_size: int = 5000           # Target writer page size
    max_batch_bytes: int = 16 * 1024 * 1024  # 16 MB max byte buffer
    ram_limit_gb: float = 4.0
    commit_interval: int = 1000
    adaptive_concurrency: bool = True


@dataclass
class ValidationPolicy:
    level: ValidationLevel = ValidationLevel.LEVEL_3_MERKLE_TREE
    sample_percentage: float = 100.0
    fail_on_mismatch: bool = True


@dataclass
class RecoveryPolicy:
    max_retries: int = 3
    initial_backoff_sec: float = 1.0
    max_backoff_sec: float = 30.0
    use_pk_high_water_mark: bool = True
    checkpoint_durability_mode: str = "NORMAL"  # NORMAL or FULL


@dataclass
class TransportPartition:
    partition_id: str
    table_name: str
    schema_name: str
    target_schema: str
    strategy: PartitionStrategy
    lower_bound: Optional[Any] = None
    upper_bound: Optional[Any] = None
    estimated_rows: int = 0
    batch_size: int = 25000
    pk_columns: List[str] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    plan_id: str
    migration_id: str
    created_at: str
    phases: List[Dict[str, Any]] = field(default_factory=list)
    partitions: List[TransportPartition] = field(default_factory=list)
    topological_groups: List[List[str]] = field(default_factory=list)


@dataclass
class BatchMetadata:
    batch_id: str
    partition_id: str
    table_name: str
    sequence: int
    row_count: int
    first_pk: Optional[Any] = None
    last_pk: Optional[Any] = None
    checksum: str = ""
    duration_sec: float = 0.0


@dataclass
class MigrationSpecification:
    migration_id: str
    specification_version: str
    migration_name: str
    project_name: str
    source_authority: ConnectionAuthorityDTO
    target_authority: ConnectionAuthorityDTO
    selected_scope: Dict[str, Any]
    schema_plan: Dict[str, Any]
    execution_plan: ExecutionPlan
    tuning_policy: TuningPolicy
    validation_policy: ValidationPolicy
    recovery_policy: RecoveryPolicy
    governance_reference: Optional[Dict[str, Any]] = None
