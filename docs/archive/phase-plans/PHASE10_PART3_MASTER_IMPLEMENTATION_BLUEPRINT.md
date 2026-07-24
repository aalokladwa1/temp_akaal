# AKAAL Phase 10 Part 3 – Enterprise Multi-Tenant Workflow Composition, Parallel Execution & Distributed Resilience Platform
## Master Engineering Blueprint & Architecture Implementation Plan

**Document Version:** 1.0.0 (Frozen Master Blueprint)  
**Target Architectural Contract:** `PHASE10_PART1_IMPLEMENTATION_PLAN.md` (v1.3.0 Frozen)  
**Status:** **FROZEN & CERTIFIED FOR PHASE 10 PART 3 IMPLEMENTATION**  
**Authored By:** Chief Software Architect, Enterprise Solution Architect, Principal Engineer, SRE Lead, Security Lead, ARB  

---

## 1. Executive Summary

This blueprint defines the definitive enterprise engineering architecture for **AKAAL Phase 10 Part 3**: **Enterprise Multi-Tenant Workflow Composition, Parallel Execution, Cluster Orchestration & Distributed Resilience Platform**.

Building seamlessly upon Phase 10 Part 1 (Workflow Platform Core) and Phase 10 Part 2 (Eight Core Enterprise Workflow Features), Part 3 introduces:
1. **Multi-Tenant Workflow Isolation & Quota Subsystem**: Strict tenant boundaries, resource quota allocation, and tenant-scoped security contexts.
2. **Enterprise Workflow Composition Engine**: DAG composition root, composite workflows, nested workflows, parallel execution groups, and barrier synchronization (`WorkflowComposer`, `CompositeWorkflow`, `WorkflowDependencyGraph`, `WorkflowCriticalPathAnalyzer`).
3. **Distributed Lock Leasing & Concurrency Platform**: Multi-worker distributed lease locks (`IWorkflowLock` with TTL extension, fence tokens, and heartbeat renewal).
4. **Distributed Crash Recovery & Worker Failover Engine**: Automatic worker node crash detection, unacknowledged lock reclaiming, checkpoint state restoration, and transparent execution re-queueing.
5. **Enterprise Distributed Tracing, Observability & Cluster Health Subsystem**: OpenTelemetry-compatible trace parent propagation, health probes, throughput metrics, and cluster node status monitoring.

---

## 2. Complete Architecture Overview

```
                      [ AKAAL Enterprise Workflow Platform ]
                                (Phase 10 Part 3)
                                        │
    ┌───────────────────────────────────┼───────────────────────────────────┐
    ▼                                   ▼                                   ▼
[Tenant Isolation & Quota]     [Workflow Composition Engine]    [Distributed Lock Platform]
(Quota Enforcement, Context)  (DAG Trees, Barrier Synchronization) (Fence Tokens, Lease Heartbeats)
    │                                   │                                   │
    └───────────────────────────────────┼───────────────────────────────────┘
                                        ▼
    ┌───────────────────────────────────┼───────────────────────────────────┐
    ▼                                   ▼                                   ▼
[Distributed Worker Failover]  [Cluster Health & Probes]       [Tracing & Observability]
(Crash Reclaiming, Re-queue)  (Heartbeats, Worker Status)    (TraceParent, Metrics)
    │                                   │                                   │
    └───────────────────────────────────┼───────────────────────────────────┘
                                        ▼
                        [ Enterprise Core Foundation ]
             (Part 1 Platform Engine + Part 2 Concrete Workflows)
```

- **Zero Boundary Leaks**: Workflow composition coordinates workflow manifests and steps without absorbing migration SQL, row copying, or database driver mechanics.
- **Pure Dependency Injection**: All clocks, UUID generators, lease locks, event dispatchers, and storage adapters remain 100% dependency-injected.

---

## 3. Feature Breakdown

### Feature 1: Multi-Tenant Workflow Isolation & Quota Platform
- Tenant-scoped execution queues.
- Tenant quota limits (max active concurrent workflows, max memory footprint, max execution time).
- Tenant context validation via `UserContext` and `SecurityContext`.

### Feature 2: Enterprise Workflow Composition Engine
- `WorkflowComposer`: Composition root combining multiple workflow manifests into an aggregate DAG.
- `CompositeWorkflow`: Wrapper managing parent-child workflow relationships.
- `WorkflowDependencyGraph`: Topological sorting, cycle detection, and dependency resolution.
- `WorkflowCriticalPathAnalyzer`: Identification of the execution bottleneck path in complex DAGs.
- `BarrierSynchronizationStep`: Fan-out / fan-in parallel execution barrier coordination.

### Feature 3: Distributed Lock Leasing & Concurrency Subsystem
- Lease lock interface (`IWorkflowLock`) enhanced with fencing tokens (`fence_token: int`).
- Automatic background lease renewal heartbeats.
- Distributed lock collision prevention and expired lock eviction.

### Feature 4: Distributed Crash Recovery & Worker Failover Engine
- `WorkerHealthMonitor`: Tracks active worker node heartbeats.
- `OrphanedExecutionReclaimer`: Reclaims unacknowledged lock leases from crashed worker nodes.
- `DistributedRecoveryCoordinator`: Restores orphaned execution contexts from the latest valid `WorkflowCheckpoint` and re-queues them.

### Feature 5: Cluster Tracing, Observability & Health Monitoring
- OpenTelemetry-compliant W3C `traceparent` propagation (`00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01`).
- Real-time workflow throughput metrics, step execution latency histograms, and cluster node status probes.

---

## 4. Repository Impact Analysis

| Directory Path | Action | Package Ownership | Key Responsibility |
|---|---|---|---|
| `akaal/workflow/composition/` | Create | Workflow Composition | Composite DAG assembly, dependency resolution, critical path analysis, barrier synchronization |
| `akaal/workflow/multi_tenancy/` | Create | Multi-Tenancy & Quotas | Tenant quota enforcement, tenant execution isolation, tenant resource tracking |
| `akaal/workflow/distributed/` | Create | Distributed Execution & Failover | Lock fencing tokens, lease heartbeats, worker failure detection, orphan reclaiming |
| `akaal/workflow/observability/` | Create | Observability & Tracing | Cluster tracing, health probes, W3C traceparent propagation, throughput metrics |
| `tests/unit/workflow/test_composition.py` | Create | Test Suite | Unit tests for composite workflows and barrier synchronization |
| `tests/unit/workflow/test_distributed.py` | Create | Test Suite | Unit tests for distributed locks, lease heartbeats, worker crash recovery |

---

## 5. File-by-File Implementation Plan

### 1. `akaal/workflow/composition/models.py`
- Define `CompositeWorkflowNode`, `DependencyEdge`, `BarrierSpec`, `CriticalPathReport`.

### 2. `akaal/workflow/composition/composer.py`
- `WorkflowComposer`: Combines independent workflow manifests into a composite DAG with cycle detection.

### 3. `akaal/workflow/composition/graph.py`
- `WorkflowDependencyGraph`: Topological sorting (Kahn's algorithm) and execution stage grouping.

### 4. `akaal/workflow/composition/analyzer.py`
- `WorkflowCriticalPathAnalyzer`: Computes longest duration execution path in composite DAGs.

### 5. `akaal/workflow/composition/barrier.py`
- `BarrierSynchronizationStep`: Implements `IStep` coordinating parallel fan-out join conditions.

### 6. `akaal/workflow/multi_tenancy/quota.py`
- `TenantQuotaManager`: Enforces active workflow limits and memory thresholds per `tenant_id`.

### 7. `akaal/workflow/distributed/lock.py`
- `DistributedLeaseLock`: Thread-safe lease lock with fence tokens and auto-renewal background thread.

### 8. `akaal/workflow/distributed/failover.py`
- `WorkerFailoverCoordinator`: Detects worker node heartbeats and re-queues orphaned executions.

### 9. `akaal/workflow/observability/tracing.py`
- `TracingCoordinator`: Extracts and injects W3C `traceparent` headers into `UserContext`.

---

## 6. Class-by-Class Plan

- `WorkflowComposer`: `compose(manifests: Tuple[WorkflowManifest, ...]) -> WorkflowManifest`
- `WorkflowDependencyGraph`: `topological_sort() -> Tuple[Tuple[str, ...], ...]`, `detect_cycles() -> bool`
- `WorkflowCriticalPathAnalyzer`: `analyze(manifest: WorkflowManifest, step_durations: Mapping[str, float]) -> CriticalPathReport`
- `BarrierSynchronizationStep`: `execute(context: WorkflowContext) -> WorkflowStepResult`
- `TenantQuotaManager`: `acquire_quota(tenant_id: str) -> bool`, `release_quota(tenant_id: str) -> None`
- `DistributedLeaseLock`: `acquire_lease(lease_name: str, ttl_seconds: float) -> Tuple[bool, int]`
- `WorkerFailoverCoordinator`: `register_worker_heartbeat(worker_id: str) -> None`, `reclaim_orphaned_jobs() -> List[str]`

---

## 7. Interface Design

```python
class ICompositeComposer(Protocol):
    def compose(self, manifests: Tuple[WorkflowManifest, ...]) -> WorkflowManifest: ...

class ITenantQuotaManager(Protocol):
    def check_quota(self, tenant_id: str) -> bool: ...
    def acquire_slot(self, tenant_id: str) -> bool: ...
    def release_slot(self, tenant_id: str) -> None: ...

class IDistributedLeaseLock(IWorkflowLock, Protocol):
    def acquire_fence_lease(self, resource_id: str, ttl_seconds: float) -> Tuple[bool, int]: ...
    def renew_lease(self, resource_id: str, fence_token: int) -> bool: ...
```

---

## 8. Domain Model Design

All domain models will be `@dataclass(frozen=True, slots=True)` with SHA-256 payload checksums:
- `CriticalPathReport`: `(path: Tuple[str, ...], total_estimated_ms: float, bottleneck_step: str, checksum: str)`
- `TenantQuotaConfig`: `(tenant_id: str, max_concurrent_workflows: int, max_memory_mb: float, checksum: str)`
- `WorkerNodeHeartbeat`: `(worker_id: str, last_heartbeat_at: str, active_leases: Tuple[str, ...], checksum: str)`

---

## 9. Dependency Graph

```text
Composition Layer (Composer, Graph, Analyzer, Barrier)
                      ↓
Multi-Tenancy Layer (TenantQuotaManager)
                      ↓
Distributed Layer (DistributedLeaseLock, WorkerFailoverCoordinator)
                      ↓
Observability Layer (TracingCoordinator, ClusterHealthMonitor)
                      ↓
Phase 10 Part 1 Platform Core + Part 2 Concrete Workflows
```

Strictly acyclic dependency direction. Zero imports from higher layers to lower layers.

---

## 10. Workflow Diagrams

```
[Parent Workflow] ──► [Fan-Out: Parallel Group 1 & Parallel Group 2]
                                │               │
                                ▼               ▼
                      [Child Workflow A]   [Child Workflow B]
                                │               │
                                └───────┬───────┘
                                        ▼
                          [BarrierSynchronizationStep]
                                        │
                                        ▼
                             [Continue Parent Execution]
```

---

## 11. Sequence Diagrams

```text
WorkerNode            DistributedLeaseLock        FailoverCoordinator        CheckpointManager
    │                          │                           │                         │
    ├───── acquire_lease() ───►│                           │                         │
    │◄──── (success, fence=42)─┤                           │                         │
    │                          │                           │                         │
  [CRASH]                      │                           │                         │
                               ├──── heartbeat timeout ───►│                         │
                               │                           ├───── load_latest() ────►│
                               │                           │◄──── (context) ─────────┤
                               │                           ├───── re-queue job ─────►│
```

---

## 12. State Machine Design

Extends existing explicit 12-state `WorkflowState` machine:
- Add multi-tenant sub-states: `TENANT_QUOTA_WAITING`.
- Add barrier sub-states: `BARRIER_WAITING`, `BARRIER_RELEASED`.
- All transitions audited under atomic `StateController._lock`.

---

## 13. Event Flow

New domain events emitted via `IEventDispatcher`:
- `TenantQuotaExceededEvent`
- `WorkflowComposedEvent`
- `BarrierReachedEvent`
- `BarrierReleasedEvent`
- `WorkerNodeCrashedEvent`
- `LeaseReclaimedEvent`

---

## 14. API Contracts

Stable client facade extension in `akaal/workflow/api/client.py`:
- `WorkflowClient.submit_composite_workflow(manifests: List[WorkflowManifest], tenant_id: str) -> str`
- `WorkflowClient.get_critical_path(workflow_id: str) -> CriticalPathReport`
- `WorkflowClient.get_tenant_quota_status(tenant_id: str) -> dict`

---

## 15. Error Handling Strategy

Structured exception hierarchy extending `WorkflowException`:
- `TenantQuotaExceededException`
- `WorkflowCyclicDependencyException`
- `BarrierTimeoutException`
- `FencingTokenInvalidException`
- `WorkerNodeUnreachableException`

---

## 16. Recovery Strategy

1. Worker crash detected after missing 3 consecutive heartbeats (30 seconds).
2. Lock leases associated with dead worker fenced using `fence_token`.
3. Execution restored from latest `WorkflowCheckpoint` via `CheckpointManager`.
4. Job re-queued to an active worker node with preserved correlation ID.

---

## 17. Checkpoint Strategy

- Checkpoint created automatically at:
  1. Composition root initialization.
  2. Entry to `BarrierSynchronizationStep`.
  3. Exit from `BarrierSynchronizationStep`.
  4. Worker crash recovery re-queue point.

---

## 18. Retry Strategy

- Exponential backoff with jitter for transient lock collisions.
- Tenant quota waiting retries with 5-second polling intervals up to configurable max wait time.

---

## 19. Concurrency Strategy

- Thread-safe collections protected by `threading.Lock()`.
- Fence tokens (`fence_token: int`) incremented atomically on lease acquisition, preventing stale worker writes.

---

## 20. Security Strategy

- `TenantQuotaManager` validates tenant isolation against `UserContext.tenant_id`.
- Fencing tokens prevent split-brain write corruption across distributed worker nodes.
- Cryptographic SHA-256 payload checksums on all composite manifests and barrier tokens.

---

## 21. Performance Strategy

- Sub-millisecond DAG topological sorting via Kahn's algorithm $O(|V| + |E|)$.
- Zero disk IO for barrier synchronization (in-memory atomic counters with storage backup).

---

## 22. Memory Strategy

- Slotted dataclasses (`slots=True`) across all composite graph nodes.
- In-memory event dispatcher buffer pruned automatically upon event processing.

---

## 23. Scalability Strategy

- Multi-tenant tenant-scoped execution queues prevent single high-volume tenant from starving other tenants.
- Horizontal worker node scaling supported via distributed lease locks.

---

## 24. Observability Strategy

- Full W3C `traceparent` context propagation across parent and child composite workflows.
- Prometheus-ready metrics: `akaal_workflow_composite_duration_seconds`, `akaal_tenant_active_workflows`, `akaal_worker_heartbeat_status`.

---

## 25. Audit Strategy

- Immutable audit records written to `AuditLogger` for:
  - `TENANT_QUOTA_EXCEEDED`
  - `COMPOSITE_WORKFLOW_STARTED`
  - `BARRIER_REACHED`
  - `WORKER_NODE_CRASHED`
  - `LEASE_RECLAIMED`

---

## 26. Logging Strategy

- Structured JSON log output with trace ID, tenant ID, workflow ID, and worker node ID.

---

## 27. Configuration Strategy

- Configurable via `RuntimeContext.transient_parameters`:
  - `max_tenant_concurrent_workflows` (default: 10)
  - `lease_ttl_seconds` (default: 15.0)
  - `heartbeat_interval_seconds` (default: 5.0)
  - `worker_crash_threshold_seconds` (default: 30.0)

---

## 28. Testing Strategy

- Unit tests for:
  - Topological sorting & cycle detection in `test_composition.py`.
  - Critical path analysis.
  - Multi-tenant quota enforcement.
  - Fence token lease acquisition & renewal.
  - Worker failure recovery simulation.

---

## 29. Integration Strategy

- `WorkflowClient` serves as single unified composition root for Part 1, Part 2, and Part 3 subsystems.

---

## 30. Documentation Plan

- Maintain `PHASE10_PART3_MASTER_IMPLEMENTATION_BLUEPRINT.md`.
- Document API facade changes in `docs/WORKFLOW_COMPOSITION_GUIDE.md`.

---

## 31. Git Strategy

- Standard Git flow:
  ```bash
  git status
  git add -A
  git commit -m "feat(phase10): implement part 3 multi-tenant composition and distributed resilience"
  git push origin main
  git pull --rebase origin main
  ```

---

## 32. Rollback Strategy

- In case of composite workflow failure, `RollbackWorkflow` is triggered across all completed child workflows in reverse topological order.

---

## 33. Deployment Considerations

- Zero external infrastructure hard dependencies for single-node execution.
- Redis/PostgreSQL adapter support for distributed multi-node clusters.

---

## 34. Risk Register

| Risk ID | Category | Severity | Mitigation |
|---|---|:---:|---|
| RSK-P3-01 | Cyclic dependencies in complex composite DAGs | High | Pre-execution Kahn's algorithm cycle detection |
| RSK-P3-02 | Split-brain worker writes during network partitions | Critical | Monotonically increasing fencing tokens (`fence_token`) |
| RSK-P3-03 | Tenant starvation under heavy workload | Medium | Fair-share tenant quota queue allocation |

---

## 35. Acceptance Criteria

1. 100% type hint annotation coverage across all new Part 3 files.
2. Zero circular dependencies across `akaal/workflow/`.
3. Zero un-injected time or UUID calls outside `utils/`.
4. Successful topological sort and cycle detection for composite workflows.
5. Successful barrier synchronization across parallel execution groups.
6. Successful worker crash recovery simulation.
7. All workspace unit tests passing with zero regressions.

---

## 36. Definition of Done

- All 5 Part 3 features implemented.
- Comprehensive unit and integration test suite passing.
- AST static analysis audit passed (100% type annotations, 0 circular imports).
- Git repository clean and synchronized with `origin/main`.

---

## 37. Improvements Made Over Initial Plan

During the Independent Architecture Review Board critical review, the following enterprise improvements were introduced:
1. **Fencing Tokens for Lease Locks**: Added monotonically increasing `fence_token` to `DistributedLeaseLock` to prevent split-brain stale worker writes during network partitions.
2. **Barrier Synchronization Step**: Replaced ad-hoc thread polling with a formal `BarrierSynchronizationStep` implementing `IStep` for deterministic fan-out / fan-in execution.
3. **Kahn's Topological Cycle Detection**: Explicitly integrated $O(|V| + |E|)$ cycle detection in `WorkflowComposer` before execution manifest generation.
4. **Tenant Isolation Quota Manager**: Added explicit multi-tenant quota tracking to prevent single tenant resource hogging.
5. **W3C TraceParent Propagation**: Embedded standard OpenTelemetry W3C traceparent headers into `UserContext` for distributed tracing across parent and child workflows.

---

## 38. Frozen Plan Certification & Execution Freeze Notice

The **AKAAL Phase 10 Part 3 Master Implementation Blueprint** is hereby **FORMALLY CERTIFIED AND FROZEN**.

**Execution Freeze Notice**: Zero production source code shall be written until the explicit execution prompt is received.
