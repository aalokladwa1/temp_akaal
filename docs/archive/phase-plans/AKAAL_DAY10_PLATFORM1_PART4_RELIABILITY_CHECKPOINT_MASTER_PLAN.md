# AKAAL DAY 10 — PLATFORM 1 PART 4: FAULT TOLERANCE, CHECKPOINTING & STATE MANAGEMENT
## MASTER IMPLEMENTATION PLANNING CONTRACT (VERSION 2.0)
**Status:** Permanent Architecture Blueprint & Reliability Engineering Contract (Frozen & ARB Certified)  
**Target Subsystem:** `akaal.platform.streaming.checkpoint`, `akaal.platform.streaming.state`, `akaal.platform.streaming.recovery` (Platform 1 Part 4 - Reliability Subsystem)  
**Base Architecture:** Built directly upon frozen Platform 1 Part 1 (`akaal.platform.streaming`), Part 2 (`akaal.platform.streaming.runtime`), and Part 3 (`akaal.platform.streaming.memory`).

---

## 1. Executive Summary & ARB Reliability Architecture Refinements (Version 2.0)

This Master Implementation Planning Contract Version 2.0 establishes the permanent, reference-grade engineering contract for **Platform 1 Part 4: Fault Tolerance, Checkpointing & State Management**. 

Evaluated and strengthened by an Independent Architecture Review Board (ARB), Version 2.0 evolves the reliability subsystem into a transactional, epoch-aligned, multi-domain fault-tolerant engine matching or exceeding Apache Flink, FoundationDB, CockroachDB, and Akka Persistence architectures.

### Core Architectural Innovations in Version 2.0
1. **Multi-Tier Recovery Domains**: Segregates recovery into 7 explicit domains: Task, Operator, Pipeline, Runtime, Node, Cluster, and Disaster Recovery.
2. **Checkpoint Epoch System**: Groups checkpoints under monotonic `CheckpointEpoch` umbrellas (e.g. `Epoch 145` $\rightarrow$ `Checkpoint 145.1`, `145.2`, `145.3`) to guarantee $100\%$ deterministic replay and auditability.
3. **Transactional State Operations (`StateTransaction`)**: Enforces ACID-style state mutations: `Begin` $\rightarrow$ `Mutate` $\rightarrow$ `Validate` $\rightarrow$ `Commit` $\rightarrow$ `Rollback`.
4. **10-State Recovery Finite State Machine (Recovery FSM)**: Formalizes recovery orchestration across 10 explicit states: `IDLE`, `DETECTING`, `CLASSIFYING`, `PREPARING`, `RESTORING`, `REPLAYING`, `VALIDATING`, `RESUMING`, `COMPLETE`, `FAILED`.
5. **Centralized Checkpoint Registry & Snapshot Catalog**: `CheckpointRegistry` serves as the authoritative source for checkpoint validation and retention, while `SnapshotCatalog` tracks lineage, checksums, and schema versions.
6. **Encapsulated `RecoveryContext`**: Immutable parameter object encapsulating Checkpoint ID, Epoch, Failure Reason, Recovery Policy, Replay Cursor, and Trace Context across all recovery calls.
7. **Explicit Configurable Consistency Levels**: Supports 4 formal consistency modes: `BestEffort`, `AtLeastOnce`, `ExactlyOnce`, and `StrictTransactional`.
8. **State Capability Registry (`StateCapabilityRegistry`)**: Discovers and advertises backend capabilities (`SupportsIncrementalCheckpoint`, `SupportsTransactions`, `SupportsAsyncSnapshot`, `SupportsTTL`).
9. **Pluggable Replay Policy Engine**: Decouples `FastReplay`, `DeterministicReplay`, `ValidationReplay`, `PartialReplay`, and `FullReplay` policies.
10. **Executable Reliability Assertions & Health Model**: Real-time assertion engine enforcing 0 missing barriers, 0 replay gaps, and 0 orphaned snapshots alongside multi-domain reliability health scoring.

---

## 2. Reliability Evolution Guidelines & Architectural Principles

The following 10 architectural principles govern the evolution of Platform 1 Part 4:

1. **Preserve Deterministic Replay**: Any state recovery or replay operation must yield identical execution results regardless of execution environment or node hardware.
2. **Preserve Checkpoint Ordering**: Checkpoint barriers must be processed and committed in strict monotonic sequence order.
3. **Encapsulate `StateManager`**: All state modifications must pass through `StateManager` and `StateTransaction` bridges; direct state storage access is strictly prohibited.
4. **Encapsulate `CheckpointCoordinator`**: No operator or worker task may trigger or alter checkpoint metadata without routing through `CheckpointCoordinator`.
5. **Maintain Explicit Consistency Guarantees**: Configured consistency levels (`ExactlyOnce`, `AtLeastOnce`) must be strictly honored across all recovery scenarios.
6. **Idempotent Recovery Operations**: Executing a recovery workflow multiple times with the same `RecoveryContext` must produce identical state graphs.
7. **Zero Replay Gaps**: The WAL replay engine must assert continuous sequence coverage without missing or duplicated log offsets.
8. **Strict Snapshot Lineage Auditability**: Every snapshot entry in `SnapshotCatalog` must reference its parent snapshot ID, creation timestamp, and SHA-256 binary digest.
9. **Backward Schema Compatibility**: State schema evolution must maintain backward compatibility using `StateVersioning` and `StateMigration` handlers.
10. **Isolated Failure Blast Radii**: Recovery must be executed in the lowest possible recovery domain (e.g., Task Recovery before Node Recovery).

---

## 3. Architecture Decision Records for Reliability Subsystem (V2.0)

### ADR-026: Multi-Domain Recovery Isolation
- **Status**: Approved / Frozen
- **Context**: Triggering cluster-wide failover for a single task thread crash wastes cluster resources and degrades throughput.
- **Decision**: Defines 7 explicit recovery domains. Faults are handled at the narrowest domain boundary (`TaskRecoveryDomain`) before escalating to higher domains (`PipelineRecoveryDomain`, `NodeRecoveryDomain`).
- **Consequences**: Minimizes recovery latency and blast radius.

### ADR-027: Transactional State Mutation Protocol (`StateTransaction`)
- **Status**: Approved / Frozen
- **Context**: Partial state writes during worker thread crashes corrupt local RocksDB/Memory states.
- **Decision**: Operator state writes execute inside `StateTransaction` journals. Mutations are staged in memory and committed atomically upon successful checkpoint barrier alignment.
- **Consequences**: Guarantees zero state corruption upon unhandled worker crashes.

### ADR-028: Centralized Checkpoint Registry & Snapshot Catalog
- **Status**: Approved / Frozen
- **Context**: Distributing metadata across individual tasks makes auditability and garbage collection error-prone.
- **Decision**: All snapshot metadata is registered in a thread-safe `CheckpointRegistry` and indexed in `SnapshotCatalog`.
- **Consequences**: Provides single-source-of-truth metadata inspection for operators and automated cleanup.

### ADR-029: 10-State Checkpoint Lifecycle Specification
- **Status**: Approved / Frozen
- **Context**: Unclear checkpoint lifecycle leads to orphaned snapshot files on storage backends.
- **Decision**: Every checkpoint transitions through 10 explicit states: `CREATED` $\rightarrow$ `SCHEDULED` $\rightarrow$ `INJECTED` $\rightarrow$ `ALIGNING` $\rightarrow$ `SNAPSHOTTING` $\rightarrow$ `VALIDATING` $\rightarrow$ `COMMITTED` $\rightarrow$ `RETAINED` $\rightarrow$ `EXPIRED` $\rightarrow$ `DELETED`.
- **Consequences**: Ensures $100\%$ deterministic retention and storage garbage collection.

### ADR-030: Executable Reliability Assertion Engine
- **Status**: Approved / Frozen
- **Context**: Silent data corruption or barrier loss can go undetected until output sinks emit corrupted streams.
- **Decision**: `ReliabilityAssertionEngine` validates runtime invariants (no missing barriers, no replay gaps, no duplicate IDs) at every checkpoint boundary.
- **Consequences**: Catches stream anomalies immediately before state commit.

---

## 4. Repository Structure & Folder Layout

Platform 1 Part 4 resides in `akaal/platform/streaming/checkpoint/`, `state/`, `recovery/`, `catalog/`, and `transactions/`:

```
temp_akaal-main/
├── akaal/
│   ├── platform/
│   │   └── streaming/
│   │       ├── catalog/                       # Snapshot Catalog & Lineage Tracking
│   │       │   ├── __init__.py
│   │       │   ├── checkpoint_registry.py
│   │       │   └── snapshot_catalog.py
│   │       ├── checkpoint/                    # Checkpoint & Epoch Coordinator
│   │       │   ├── __init__.py
│   │       │   ├── async_snapshot_engine.py
│   │       │   ├── barrier_aligner.py
│   │       │   ├── barrier_coordinator.py
│   │       │   ├── barrier_tracker.py
│   │       │   ├── checkpoint_coordinator.py
│   │       │   ├── checkpoint_epoch.py
│   │       │   ├── checkpoint_lifecycle.py
│   │       │   ├── checkpoint_manager.py
│   │       │   ├── checkpoint_metadata.py
│   │       │   ├── checkpoint_scheduler.py
│   │       │   ├── checkpoint_storage.py
│   │       │   ├── epoch_coordinator.py
│   │       │   ├── incremental_checkpoint.py
│   │       │   ├── snapshot_lifecycle.py
│   │       │   ├── snapshot_manager.py
│   │       │   ├── snapshot_store.py
│   │       │   └── snapshot_validator.py
│   │       ├── recovery/                      # Recovery FSM, Domains & Replay Engine
│   │       │   ├── __init__.py
│   │       │   ├── assertions_engine.py
│   │       │   ├── at_least_once_coordinator.py
│   │       │   ├── consistency_engine.py
│   │       │   ├── consistency_levels.py
│   │       │   ├── consistency_validator.py
│   │       │   ├── disaster_recovery.py
│   │       │   ├── exactly_once_coordinator.py
│   │       │   ├── failure_classifier.py
│   │       │   ├── failure_detector.py
│   │       │   ├── log_segment_manager.py
│   │       │   ├── offset_manager.py
│   │       │   ├── recovery_context.py
│   │       │   ├── recovery_coordinator.py
│   │       │   ├── recovery_domains.py
│   │       │   ├── recovery_fsm.py
│   │       │   ├── recovery_health.py
│   │       │   ├── recovery_manager.py
│   │       │   ├── recovery_policy_engine.py
│   │       │   ├── replay_cursor.py
│   │       │   ├── replay_engine.py
│   │       │   ├── replay_planner.py
│   │       │   ├── replay_policies.py
│   │       │   ├── rollback_manager.py
│   │       │   └── write_ahead_log.py
│   │       ├── state/                         # State Management & Capabilities
│   │       │   ├── __init__.py
│   │       │   ├── broadcast_state_manager.py
│   │       │   ├── in_memory_backend.py
│   │       │   ├── keyed_state_manager.py
│   │       │   ├── operator_state_manager.py
│   │       │   ├── redis_backend.py
│   │       │   ├── rocksdb_backend.py
│   │       │   ├── state_backend_bridge.py
│   │       │   ├── state_capabilities.py
│   │       │   ├── state_compaction.py
│   │       │   ├── state_manager.py
│   │       │   ├── state_migration.py
│   │       │   ├── state_registry.py
│   │       │   ├── state_versioning.py
│   │       │   └── window_state_manager.py
│   │       └── transactions/                  # Transactional State Protocol
│   │           ├── __init__.py
│   │           ├── state_transaction.py
│   │           └── transaction_coordinator.py
```

---

## 5. Subsystem Package & Module Taxonomy

Catalog for all 58 Part 4 Python modules across 5 package namespaces:

1. `catalog.checkpoint_registry`: Centralized registry managing checkpoint lookup, indexing, and retention.
2. `catalog.snapshot_catalog`: Catalog indexing snapshot versions, lineage, and SHA-256 checksums.
3. `checkpoint.checkpoint_epoch`: Represents checkpoint epoch umbrellas (e.g. `Epoch 145`).
4. `checkpoint.epoch_coordinator`: Coordinates epoch transitions and epoch retention policies.
5. `checkpoint.checkpoint_lifecycle`: Governs 10-state checkpoint lifecycle transitions.
6. `recovery.recovery_domains`: Defines 7 explicit recovery domains (Task, Node, Disaster).
7. `recovery.recovery_fsm`: 10-state Finite State Machine orchestrating recovery workflows.
8. `recovery.recovery_context`: Immutable parameter object encapsulating recovery execution context.
9. `recovery.consistency_levels`: Defines consistency modes (`BestEffort`, `AtLeastOnce`, `ExactlyOnce`, `StrictTransactional`).
10. `recovery.replay_policies`: Pluggable replay behavior policies (`FastReplay`, `DeterministicReplay`).
11. `recovery.assertions_engine`: Executable assertions validating runtime reliability invariants.
12. `recovery.recovery_health`: Computes real-time composite reliability health scores.
13. `state.state_capabilities`: Registry advertising state backend features (`SupportsTransactions`, `SupportsIncremental`).
14. `transactions.state_transaction`: Transactional journal staging state modifications.
15. `transactions.transaction_coordinator`: Manages 2PC state transaction commits and rollbacks.

---

## 6. Multi-Tier Recovery Domains

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       DisasterRecoveryDomain (Cross-Region)                  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ (Escalation)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                        ClusterRecoveryDomain (Failover)                      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ (Escalation)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                         NodeRecoveryDomain (Worker Restarts)                 │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ (Escalation)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    Pipeline / TaskRecoveryDomain (Localized)                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Recovery Finite State Machine (Recovery FSM)

```
[IDLE] ──► [DETECTING] ──► [CLASSIFYING] ──► [PREPARING] ──► [RESTORING]
                                                                 │
                                                                 ▼
[COMPLETE] ◄── [RESUMING] ◄── [VALIDATING] ◄── [REPLAYING] ◄─────┘
    │
    ▼ (On Recovery Error)
[FAILED]
```

```python
# akaal/platform/streaming/recovery/recovery_fsm.py
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional
from akaal.platform.streaming.recovery.recovery_context import RecoveryContext

class RecoveryFSMState(Enum):
    IDLE = auto()
    DETECTING = auto()
    CLASSIFYING = auto()
    PREPARING = auto()
    RESTORING = auto()
    REPLAYING = auto()
    VALIDATING = auto()
    RESUMING = auto()
    COMPLETE = auto()
    FAILED = auto()

class RecoveryFSMController:
    """Manages 10-state recovery execution workflows."""

    def __init__(self, context: RecoveryContext) -> None:
        self.context = context
        self._state = RecoveryFSMState.IDLE

    def transition_to(self, target_state: RecoveryFSMState) -> None:
        self._state = target_state

    @property
    def current_state(self) -> RecoveryFSMState:
        return self._state
```

---

## 8. Transactional State Mutation Protocol

```python
# akaal/platform/streaming/transactions/state_transaction.py
from typing import Dict, Any, Optional

class StateTransaction:
    """ACID-style transactional state mutation journal."""

    def __init__(self, transaction_id: str, operator_id: str) -> None:
        self.transaction_id = transaction_id
        self.operator_id = operator_id
        self._staged_mutations: Dict[bytes, bytes] = {}
        self._is_active = True

    def mutate(self, key: bytes, value: bytes) -> None:
        if not self._is_active:
            raise RuntimeError("Cannot mutate an inactive transaction.")
        self._staged_mutations[key] = value

    def commit(self, target_store: Dict[bytes, bytes]) -> None:
        if not self._is_active:
            raise RuntimeError("Cannot commit an inactive transaction.")
        target_store.update(self._staged_mutations)
        self._is_active = False

    def rollback(self) -> None:
        self._staged_mutations.clear()
        self._is_active = False
```

---

## 9. Performance SLAs & Benchmark Targets

| Performance Metric | Apache Flink Benchmark Target | AKAAL Part 4 V2.0 SLA |
| :--- | :--- | :--- |
| **Checkpoint Coordination Latency** | < 1,000 milliseconds | < 150 milliseconds |
| **Barrier Alignment Overhead** | < 5.0 milliseconds | < 0.3 milliseconds |
| **Incremental Snapshot Commit** | < 2,000 milliseconds | < 400 milliseconds |
| **WAL Replay Throughput** | > 500,000 records/sec | > 1,800,000 records/sec |
| **Localized Task Recovery SLA** | < 3,000 milliseconds | < 500 milliseconds (Recovery FSM) |
| **End-to-End Exactly-Once Overhead** | < 10% throughput drop | < 2% throughput drop |

---

## 10. Definition of Done (Version 2.0 Certification)

The implementation of **Platform 1 Part 4: Fault Tolerance, Checkpointing & State Management** is defined as officially COMPLETE when:

1. All 58 specified modules across 5 package namespaces under `akaal/platform/streaming/` (`checkpoint/`, `state/`, `recovery/`, `catalog/`, `transactions/`) are fully implemented.
2. Static type checker `mypy --strict akaal/platform/streaming/checkpoint akaal/platform/streaming/state akaal/platform/streaming/recovery akaal/platform/streaming/catalog akaal/platform/streaming/transactions` returns 0 errors.
3. All 15 mandatory ARB enterprise improvements (Recovery Domains, Checkpoint Epochs, State Transactions, Recovery FSM, Checkpoint Registry, Snapshot Catalog, RecoveryContext, Consistency Levels, State Capabilities, Replay Policies, Subsystem Contracts, Health Model, Reliability Assertions, 10-State Checkpoint Lifecycle, Evolution Guidelines) are verified.
4. Asynchronous Chandy-Lamport barrier snapshotting and state replay engines pass 100 consecutive automated chaos fault recovery runs with zero data loss or duplicate emissions.
5. The Architecture Review Board (ARB) formally signs off on the Part 4 Version 2.0 release certification report.
