# AKAAL Phase 10 – Enterprise Workflow & Orchestration Platform
## Part 2: Concrete Workflows & Enterprise Orchestration Master Implementation Plan

**Document Version:** 1.0.0  
**Target Architectural Contract:** `PHASE10_PART1_IMPLEMENTATION_PLAN.md` (v1.3.0 Frozen)  
**Status:** Implementation Blueprint & Engineering Roadmap (Approved for Planning)  

---

## 1. Executive Summary

This document establishes the master engineering implementation plan for **AKAAL Phase 10 - Part 2: Concrete Workflows & Enterprise Orchestration**. Building on top of the certified Phase 10 Part 1 platform foundation (`akaal/workflow/`), Part 2 implements the six mission-critical enterprise migration workflows, human-in-the-loop approval gates, workflow composition, scheduling, notification handling, audit logging integration, and future distributed worker compatibility.

All implementations strictly conform to the frozen v1.3.0 architectural blueprint. Zero architectural redesign is permitted. Part 2 transforms the generic orchestration engine into a fully operational, enterprise-certified workflow system.

---

## 2. Scope Definition

Part 2 encompasses six core concrete workflows and five platform orchestration capabilities:

### A. Concrete Enterprise Workflows
1. **`PreMigrationWorkflow`**: Orchestrates environment discovery, target schema pre-flight verification, source database snapshotting, and migration readiness checks.
2. **`MigrationWorkflow`**: Orchestrates bulk data extract-transform-load sequences, parallel table streaming, batch checkpointing, and error threshold monitoring.
3. **`ValidationWorkflow`**: Orchestrates target schema equivalence validation, row count verification, data checksum comparison, and Golden Benchmark validation.
4. **`CutoverWorkflow`**: Orchestrates source traffic locking, final Change Data Capture (CDC) catch-up, read-only window enforcement, and DNS/Connection target cutover.
5. **`RollbackWorkflow`**: Orchestrates emergency cutover abort, source traffic unlocking, target database teardown, and fallback state restoration.
6. **`ApprovalWorkflow`**: Orchestrates human-in-the-loop approval requests, approval token verification, timeout escalation, and sign-off logging.

### B. Enterprise Platform Capabilities
- **Human-in-the-Loop Approval Gates (`akaal/workflow/approval/`)**: Token-based approval gates with expiration TTLs, security context validation, and audit logging.
- **Workflow Composition (`akaal/workflow/composition/`)**: Combining multiple concrete workflows into complex composite execution graphs (e.g., `PreMigration` → `Migration` → `Validation` → `Approval` → `Cutover`).
- **Workflow Scheduling (`akaal/workflow/scheduling/`)**: One-shot timers and recurring cron schedules integrated with `schedule` primitives.
- **Workflow Notifications (`akaal/workflow/notifications/`)**: Event-driven alerts sent via `IEventDispatcher` on state changes, approval requests, failures, and completions.
- **Audit Subsystem Integration (`akaal/workflow/integration/`)**: Bridge connecting `IEventDispatcher` events to AKAAL's central audit logger (`akaal/audit/`).
- **Distributed Worker Preparedness**: Worker isolation protocols and payload serialization for Celery/Ray/Kubernetes execution.

---

## 3. Functional & Non-Functional Requirements

### Functional Requirements
- **FR-1**: Every concrete workflow MUST be expressible as a valid `WorkflowManifest` containing typed `StepDefinition` entries and a Directed Acyclic Graph (DAG).
- **FR-2**: All concrete workflow steps MUST implement the extended `IStep` interface contract (`initialize`, `validate_preconditions`, `execute`, `on_success`, `on_failure`, `validate_postconditions`, `checkpoint`, `resume`, `rollback`, `cleanup`).
- **FR-3**: `ApprovalWorkflow` and approval gates MUST generate cryptographically signed, SHA-256 verified `ApprovalToken` instances.
- **FR-4**: Execution MUST pause cleanly at `WAITING_FOR_APPROVAL` state when encountering an `ApprovalGateStep`, persisting a valid `WorkflowCheckpoint`.
- **FR-5**: `WorkflowComposer` MUST validate composite DAG acyclicity across workflow boundaries before submission.
- **FR-6**: `WorkflowScheduler` MUST support both one-shot fixed time triggers and recurring Cron schedule expressions.
- **FR-7**: `WorkflowNotificationService` MUST dispatch typed notifications for `WorkflowStateChanged`, `ApprovalRequested`, `StepFailed`, and `WorkflowCompleted`.
- **FR-8**: `AuditIntegrationAdapter` MUST record every state transition and step execution event in AKAAL's append-only audit trail.

### Non-Functional Requirements
- **NFR-1 (Strict Immutability)**: All domain models, context updates, and manifests MUST be `@dataclass(frozen=True)` with SHA-256 checksum validation.
- **NFR-2 (Determinism)**: Time, random values, and UUIDs MUST be injected via `IClock` and `IIdGenerator`. Zero raw system calls.
- **NFR-3 (Thread Safety)**: All registries, schedulers, and in-memory dispatchers MUST be thread-safe under `threading.Lock()`.
- **NFR-4 (Zero Boundary Leakage)**: Concrete steps MUST delegate business logic to external packages (`decoder`, `planner`, `migration`) via interfaces, never containing direct SQL or ORM calls.
- **NFR-5 (Resumability & Crash Recovery)**: Restarting any interrupted workflow MUST default to hydrating the latest checkpoint without data loss or duplicate step execution.

---

## 4. Package Responsibilities & Ownership DAG

```
akaal/workflow/
├── api/                # WorkflowClient Facade & Concrete Workflow Entrypoints
├── approval/           # Approval Engine, ApprovalToken, ApprovalGate, ApprovalRequest
├── checkpoint/         # Checkpoint Storage & Recovery Orchestration (Part 1)
├── composition/        # WorkflowComposer, WorkflowChain, CompositeWorkflow
├── concrete/           # Enterprise Workflows (PreMigration, Migration, Validation, Cutover, Rollback, Approval)
├── contracts/          # Structural Manifest & Step Definition Contract Validators (Part 1)
├── engine/             # WorkflowEngine Coordinator (Part 1)
├── events/             # Domain Event Definitions & IEventDispatcher (Part 1)
├── exceptions/         # Workflow Exception Hierarchy (Part 1)
├── execution/          # StepExecutor, ExecutionPipeline, Retry & Timeout Policies (Part 1)
├── execution_records/  # Telemetry, Trace, & Metrics Models (Part 1)
├── integration/        # Audit, Intelligence, & Migration Subsystem Adapters
├── interfaces/         # Structural Interfaces (Part 1)
├── locks/              # Distributed Concurrency Locks (Part 1)
├── models/             # Immutable Frozen Dataclasses (Part 1)
├── notifications/      # WorkflowNotificationService & Notification Handlers
├── registry/           # WorkflowStepRegistry with Private _StepFactory (Part 1)
├── scheduling/         # WorkflowScheduler, CronSchedule, OneShotSchedule
├── security/           # SecurityContext & Permission Verification (Part 1)
├── state_machine/      # WorkflowState Enum & StateController (Part 1)
├── steps/              # Base AbstractStep & Concrete Step Definitions
└── utils/              # Clock, IdGenerator, Serializer Utilities (Part 1)
```

### Component Dependency Flow (Strict DAG)
```
[api] ──> [concrete] ──> [composition] ──> [scheduling] ──> [notifications]
            │                 │                 │                 │
            ▼                 ▼                 ▼                 ▼
     [approval] ──────> [integration] ───> [engine / execution / registry]
            │                                         │
            └────────────────────┬────────────────────┘
                                 ▼
                    [Part 1 Platform Foundation]
```

---

## 5. File-by-File Implementation Plan

### Subsystem 1: Approval Engine (`akaal/workflow/approval/`)
1. **`models.py`**:
   - `ApprovalToken`: Immutable token (`token_id: str`, `workflow_id: str`, `step_id: str`, `requested_by: str`, `approved_by: Optional[str]`, `status: ApprovalStatus`, `expires_at: str`, `checksum: str`).
   - `ApprovalRequest`: Details of requested approval gate (`request_id: str`, `workflow_id: str`, `required_role: str`, `timeout_seconds: float`).
2. **`engine.py`**:
   - `ApprovalEngine`: Manages pending approval tokens, evaluates approval sign-offs, checks expirations via `IClock`, and issues resolution events.
3. **`gate.py`**:
   - `ApprovalGateStep`: Concrete `IStep` implementation that pauses execution in `WAITING_FOR_APPROVAL` state until an `ApprovalToken` is verified.

### Subsystem 2: Workflow Composition (`akaal/workflow/composition/`)
4. **`composer.py`**:
   - `WorkflowComposer`: Combines multiple `WorkflowManifest` blueprints into a single `CompositeWorkflowManifest`, recalculating topological dependencies and merged DAG acyclicity.
5. **`chain.py`**:
   - `WorkflowChain`: Sequential builder facade (`chain.then(workflow_a).then(workflow_b).with_approval()`).

### Subsystem 3: Concrete Enterprise Workflows (`akaal/workflow/concrete/`)
6. **`pre_migration.py`**:
   - `PreMigrationWorkflow`: Manifest builder for discovery, readiness check, target schema check, snapshot creation.
   - Steps: `EnvironmentDiscoveryStep`, `PreflightCheckStep`, `SourceSnapshotStep`.
7. **`migration.py`**:
   - `MigrationWorkflow`: Manifest builder for data extraction, transformation streaming, and loading.
   - Steps: `DataExtractStep`, `DataTransformStep`, `BatchLoadStep`.
8. **`validation.py`**:
   - `ValidationWorkflow`: Manifest builder for post-migration validation.
   - Steps: `RowCountValidationStep`, `ChecksumValidationStep`, `GoldenBenchmarkValidationStep`.
9. **`cutover.py`**:
   - `CutoverWorkflow`: Manifest builder for traffic cutover.
   - Steps: `SourceLockStep`, `CdcCatchupStep`, `DnsCutoverStep`.
10. **`rollback.py`**:
    - `RollbackWorkflow`: Manifest builder for emergency abort.
    - Steps: `CutoverAbortStep`, `SourceUnlockStep`, `TargetTeardownStep`.
11. **`approval.py`**:
    - `ApprovalWorkflow`: Standalone human sign-off workflow manifest.

### Subsystem 4: Scheduling Subsystem (`akaal/workflow/scheduling/`)
12. **`scheduler.py`**:
    - `WorkflowScheduler`: Manages cron-like and one-shot workflow triggers, scheduling background execution via `IClock`.
13. **`triggers.py`**:
    - `CronSchedule`: 5-field cron parser (`minute`, `hour`, `day_of_month`, `month`, `day_of_week`).
    - `OneShotSchedule`: Timestamped one-shot trigger.

### Subsystem 5: Notifications & Audit Integration (`akaal/workflow/notifications/` & `integration/`)
14. **`notifications/service.py`**:
    - `WorkflowNotificationService`: Listens to `IEventDispatcher` events and dispatches alert messages to registered notification channels.
15. **`integration/audit_adapter.py`**:
    - `AuditIntegrationAdapter`: Subscribes to `IEventDispatcher` events and transforms domain events into AKAAL `AuditRecord` entries written to `akaal/audit/`.
16. **`integration/adapters.py`**:
    - `IntelligenceAdapter`: Interface wrapper delegating step decisions to `akaal/intelligence/`.
    - `MigrationEngineAdapter`: Interface wrapper delegating execution to `akaal/migration/`.

---

## 6. Implementation Phase Breakdown

### Phase 1: Approval Engine & Token Subsystem
- **Purpose**: Establish human-in-the-loop approval gate mechanics, token issuance, and approval step lifecycle.
- **Deliverables**: `ApprovalToken`, `ApprovalRequest`, `ApprovalEngine`, `ApprovalGateStep`.
- **Files**: `akaal/workflow/approval/models.py`, `akaal/workflow/approval/engine.py`, `akaal/workflow/approval/gate.py`.
- **Dependencies**: Part 1 Platform Foundation.
- **Testing**: Unit tests for approval token signing, expiration evaluation, and gate pause/resume.
- **Complexity**: Medium | **Risk**: Low

### Phase 2: Concrete Workflow Steps & Manifest Builders
- **Purpose**: Implement the 6 concrete enterprise migration workflows and their specialized step steps.
- **Deliverables**: `PreMigrationWorkflow`, `MigrationWorkflow`, `ValidationWorkflow`, `CutoverWorkflow`, `RollbackWorkflow`, `ApprovalWorkflow`.
- **Files**: `akaal/workflow/concrete/*.py`, `akaal/workflow/steps/*.py`.
- **Dependencies**: Phase 1, Part 1 `IStep` interface.
- **Testing**: Step contract tests, mock execution runs, rollback verification.
- **Complexity**: High | **Risk**: Medium

### Phase 3: Workflow Composition Engine
- **Purpose**: Allow combining multiple workflows into unified composite execution graphs.
- **Deliverables**: `WorkflowComposer`, `WorkflowChain`, `CompositeWorkflowManifest`.
- **Files**: `akaal/workflow/composition/composer.py`, `akaal/workflow/composition/chain.py`.
- **Dependencies**: Phase 2.
- **Testing**: Multi-workflow DAG acyclicity tests, composite execution trace verification.
- **Complexity**: Medium | **Risk**: Low

### Phase 4: Workflow Scheduling Subsystem
- **Purpose**: Provide deterministic one-shot and cron-based workflow trigger scheduling.
- **Deliverables**: `WorkflowScheduler`, `CronSchedule`, `OneShotSchedule`.
- **Files**: `akaal/workflow/scheduling/scheduler.py`, `akaal/workflow/scheduling/triggers.py`.
- **Dependencies**: Phase 3, `IClock`.
- **Testing**: Fixed-clock cron evaluation tests, missed schedule recovery tests.
- **Complexity**: Medium | **Risk**: Low

### Phase 5: Notifications & Audit Subsystem Integration
- **Purpose**: Connect domain events to notification services and AKAAL's central audit trail.
- **Deliverables**: `WorkflowNotificationService`, `AuditIntegrationAdapter`, `IntelligenceAdapter`, `MigrationEngineAdapter`.
- **Files**: `akaal/workflow/notifications/service.py`, `akaal/workflow/integration/*.py`.
- **Dependencies**: Phase 4, `IEventDispatcher`.
- **Testing**: Audit event emission verification, notification handler tests.
- **Complexity**: Low | **Risk**: Low

### Phase 6: E2E Integration, Verification & Distributed Preparedness
- **Purpose**: Execute end-to-end multi-workflow migration scenarios, verify zero regressions, perform AST DAG checks, and validate worker payload serialization.
- **Deliverables**: Comprehensive E2E test suite (`tests/integration/workflow/`), certification report.
- **Files**: `tests/integration/workflow/test_e2e_migration_pipeline.py`, `docs/*`.
- **Dependencies**: Phase 1 through 5.
- **Testing**: Complete pipeline E2E tests, crash injection tests, stress tests.
- **Complexity**: High | **Risk**: Medium

---

## 7. Verification & Acceptance Criteria Gates

1. **Gate 1 (Approval & Token Gate)**: Approval tokens must expire deterministically via `IClock`; `WorkflowEngine` pauses at `WAITING_FOR_APPROVAL` state and resumes cleanly upon token approval.
2. **Gate 2 (Concrete Workflow Coverage Gate)**: All 6 enterprise workflows (`PreMigration`, `Migration`, `Validation`, `Cutover`, `Rollback`, `Approval`) build valid manifests passing `ManifestValidator`.
3. **Gate 3 (Composition Gate)**: `WorkflowComposer` successfully detects circular dependencies across composite workflow boundaries.
4. **Gate 4 (Audit & Event Gate)**: 100% of state transitions and step execution results produce corresponding audit log entries in `akaal/audit/`.
5. **Gate 5 (Zero Architecture Violations Gate)**: AST import analyzer confirms 0 circular imports, 100% type hint coverage, and 0 raw un-injected calls to `uuid4()` or `datetime.utcnow()`.
6. **Gate 6 (Full Regression Gate)**: All existing 655 unit tests + new Part 2 tests pass with 100% success.
